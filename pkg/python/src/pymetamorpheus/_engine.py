"""The shared task-run engine.

Every public verb — :func:`~pymetamorpheus.search`, ``calibrate``, ``gptmd``,
``glyco_search``, ``pipeline`` — is the *same* code path with a different TOML.
That is the project's central insight: MetaMorpheus already runs an ordered list
of TOML task configs against input files, so a binding just has to

    1. generate the current default config for each task (``CMD -g``),
    2. surgically patch the handful of parameters we expose,
    3. hand the whole task list to one CLI invocation, and
    4. surface the resulting run directory as typed results.

MetaMorpheus chains the tasks *internally* — calibration output feeds GPTMD feeds
search — so we NEVER re-implement chaining, and per BRIDGE-PARALLELISM we never
fan out CLI runs host-side (MetaMorpheus parallelizes within one process; its
thread count is a correctness surface, mzLib#1111).
"""

from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from ._errors import UsageError
from ._runner import generate_default_tomls, invoke
from ._toml import format_mods, patch_toml
from .results import RunResult, discover_tasks

#: Accepted spectra extensions. Restricted to mzML for now (G-settings): a .raw
#: run hangs on the Thermo license prompt until that is set non-interactively.
_ALLOWED_SPECTRA_SUFFIXES = {".mzml"}

#: Accepted database extensions (protein sequence DBs MetaMorpheus reads).
_ALLOWED_DB_SUFFIXES = {".fasta", ".fa", ".xml", ".gz"}


@dataclass
class Task:
    """One MetaMorpheus task: its type plus the parameters we override.

    ``task_type`` is the MetaMorpheus name used both in the generated TOML
    filename (``<task_type>Task.toml``) and, indirectly, in the output folder
    (``TaskN<task_type>Task``). ``overrides`` maps ``(section, key) -> value`` in
    the exact shape :func:`pymetamorpheus._toml.patch_toml` expects.
    """

    #: e.g. "Search", "Calibration", "Gptmd", "GlycoSearch".
    task_type: str
    overrides: dict[tuple[str | None, str], object] = field(default_factory=dict)

    @property
    def toml_filename(self) -> str:
        """The default-TOML basename MetaMorpheus emits for this task."""
        # `CMD -g` writes CalibrationTask.toml, GptmdTask.toml, SearchTask.toml,
        # GlycoSearchTask.toml. task_type already carries the right stem.
        return f"{self.task_type}Task.toml"


def common_overrides(
    *,
    precursor_tol_ppm: float | None = None,
    product_tol_ppm: float | None = None,
    fixed_mods: list[str] | None = None,
    variable_mods: list[str] | None = None,
    protease: str | None = None,
    max_missed_cleavages: int | None = None,
    min_peptide_length: int | None = None,
    max_peptide_length: int | None = None,
    max_threads: int | None = None,
) -> dict[tuple[str | None, str], object]:
    """Build the ``(section, key) -> value`` map for the CommonParameters shared
    by every task type. Only non-None arguments produce an override; anything
    left None keeps MetaMorpheus's own default from ``CMD -g``.
    """
    ov: dict[tuple[str | None, str], object] = {}
    cp = "CommonParameters"
    dp = "CommonParameters.DigestionParams"

    if precursor_tol_ppm is not None:
        ov[(cp, "PrecursorMassTolerance")] = f"±{precursor_tol_ppm:.4f} PPM"
    if product_tol_ppm is not None:
        ov[(cp, "ProductMassTolerance")] = f"±{product_tol_ppm:.4f} PPM"
    if fixed_mods is not None:
        ov[(cp, "ListOfModsFixed")] = format_mods(fixed_mods)
    if variable_mods is not None:
        ov[(cp, "ListOfModsVariable")] = format_mods(variable_mods)
    if max_threads is not None:
        if max_threads < 1:
            raise UsageError("max_threads must be >= 1.")
        ov[(cp, "MaxThreadsToUsePerFile")] = int(max_threads)
    if protease is not None:
        # MetaMorpheus stores the protease in two keys in DigestionParams.
        ov[(dp, "Protease")] = protease
        ov[(dp, "SpecificProtease")] = protease
    if max_missed_cleavages is not None:
        ov[(dp, "MaxMissedCleavages")] = int(max_missed_cleavages)
    if min_peptide_length is not None:
        ov[(dp, "MinPeptideLength")] = int(min_peptide_length)
    if max_peptide_length is not None:
        ov[(dp, "MaxPeptideLength")] = int(max_peptide_length)

    return ov


def _as_path_list(value, kind: str) -> list[Path]:
    if value is None:
        raise UsageError(f"At least one {kind} is required.")
    if isinstance(value, (str, Path)):
        value = [value]
    paths = [Path(v) for v in value]
    if not paths:
        raise UsageError(f"At least one {kind} is required.")
    return paths


def _validate_spectra(spectra) -> list[Path]:
    paths = _as_path_list(spectra, "spectra file")
    for p in paths:
        # Check the format first, so an unsupported extension always reports as
        # unsupported (even for a path that also doesn't exist).
        if p.suffix.lower() not in _ALLOWED_SPECTRA_SUFFIXES:
            raise UsageError(
                f"Unsupported spectra format {p.suffix!r} for {p.name}. "
                "pyMetaMorpheus currently accepts .mzML only; .raw support is "
                "deferred until the Thermo license can be accepted "
                "non-interactively (gap G-settings). Convert with MSConvert, or "
                "export .mzML from your instrument software."
            )
        if not p.exists():
            raise UsageError(f"Spectra file not found: {p}")
    return paths


def _validate_databases(database) -> list[Path]:
    paths = _as_path_list(database, "database")
    for p in paths:
        if p.suffix.lower() not in _ALLOWED_DB_SUFFIXES:
            raise UsageError(
                f"Unsupported database format {p.suffix!r} for {p.name}. "
                "Expected a protein database: .fasta/.fa, .xml (UniProt), or a "
                ".gz of either."
            )
        if not p.exists():
            raise UsageError(f"Database not found: {p}")
    return paths


def run_tasks(
    tasks: list[Task],
    *,
    spectra,
    database,
    output_dir,
    timeout: float | None = None,
) -> RunResult:
    """Generate + patch each task's TOML, run them as one MetaMorpheus invocation,
    and return a :class:`RunResult`.

    This is the single choke point every public verb funnels through.
    """
    if not tasks:
        raise UsageError("At least one task is required.")

    spectra_paths = _validate_spectra(spectra)
    database_paths = _validate_databases(database)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    # Stage the patched TOMLs in a scratch dir alongside the output.
    staging = Path(tempfile.mkdtemp(prefix="pymm_toml_", dir=out))
    try:
        defaults = generate_default_tomls(staging)
        task_toml_paths: list[Path] = []
        for i, task in enumerate(tasks, start=1):
            src = defaults.get(task.toml_filename)
            if src is None:
                raise UsageError(
                    f"MetaMorpheus did not generate a default config named "
                    f"{task.toml_filename!r}; available: {sorted(defaults)}."
                )
            dest = staging / f"task{i}_{task.toml_filename}"
            shutil.copyfile(src, dest)
            if task.overrides:
                applied = patch_toml(dest, task.overrides)
                missing = set(task.overrides) - set(applied)
                if missing:
                    raise UsageError(
                        f"These parameters had no matching key in "
                        f"{task.toml_filename} (MetaMorpheus schema may have "
                        f"changed): {sorted(missing)}."
                    )
            task_toml_paths.append(dest)

        args: list[str] = ["-t", *[str(p) for p in task_toml_paths]]
        args += ["-s", *[str(p) for p in spectra_paths]]
        args += ["-d", *[str(p) for p in database_paths]]
        args += ["-o", str(out), "-v", "minimal"]

        proc = invoke(args, timeout=timeout)
    finally:
        shutil.rmtree(staging, ignore_errors=True)

    result = RunResult(output_dir=out, stdout=proc.stdout, stderr=proc.stderr)
    result.tasks = discover_tasks(out)
    return result
