"""The public verbs: search, calibrate, gptmd, glyco_search, and pipeline.

Each verb builds one :class:`~pymetamorpheus._engine.Task` (or several, for a
pipeline) and funnels through the single :func:`~pymetamorpheus._engine.run_tasks`
choke point. The verbs differ only in which default TOML they patch and which
task-specific parameters they expose — the whole point of the shared engine.

The parameter surface is deliberately small: the handful of knobs a proteomics
investigator reaches for first. Everything else keeps MetaMorpheus's own default
from ``CMD -g``. Widen only on demand (gap G-tasks / G-demand), never speculatively.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from ._engine import (
    Task,
    common_overrides,
    normalize_params,
    run_tasks,
)
from ._errors import UsageError
from ._runner import generate_default_tomls
from ._toml import read_sections
from .results import RunResult

__all__ = [
    "search",
    "calibrate",
    "gptmd",
    "glyco_search",
    "xl_search",
    "pipeline",
    "run_toml",
    "available_parameters",
    "Task",
    "make_search_task",
    "make_calibration_task",
    "make_gptmd_task",
    "make_glyco_search_task",
    "make_xl_search_task",
    "task_from_toml",
]


# --------------------------------------------------------------------------- #
# Task builders — each returns a Task (type + patched-parameter map) without
# running anything, so pipeline() can compose them.
# --------------------------------------------------------------------------- #

def make_search_task(
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
    quantify: bool | None = None,
    match_between_runs: bool | None = None,
    normalize: bool | None = None,
    quantify_ppm_tol: float | None = None,
    write_spectral_library: bool | None = None,
    update_spectral_library: bool | None = None,
    params: dict | None = None,
) -> Task:
    """A classic ``SearchTask`` with the common parameters overridden.

    Quantification (FlashLFQ) is part of the search task and is ON by default in
    MetaMorpheus, producing ``AllQuantifiedProteinGroups.tsv`` /
    ``AllQuantifiedPeptides.tsv`` / ``AllQuantifiedPeaks.tsv``. Spectral-library
    generation is OFF by default — set ``write_spectral_library=True`` to have the
    search emit a ``.msp`` spectral library. All the knobs below map to
    ``[SearchParameters]``; leave them None to keep MetaMorpheus's defaults.
    """
    overrides = common_overrides(
        precursor_tol_ppm=precursor_tol_ppm,
        product_tol_ppm=product_tol_ppm,
        fixed_mods=fixed_mods,
        variable_mods=variable_mods,
        protease=protease,
        max_missed_cleavages=max_missed_cleavages,
        min_peptide_length=min_peptide_length,
        max_peptide_length=max_peptide_length,
        max_threads=max_threads,
    )
    sp = "SearchParameters"
    if quantify is not None:
        overrides[(sp, "DoLabelFreeQuantification")] = bool(quantify)
    if match_between_runs is not None:
        overrides[(sp, "MatchBetweenRuns")] = bool(match_between_runs)
    if normalize is not None:
        overrides[(sp, "Normalize")] = bool(normalize)
    if quantify_ppm_tol is not None:
        overrides[(sp, "QuantifyPpmTol")] = float(quantify_ppm_tol)
    if write_spectral_library is not None:
        overrides[(sp, "WriteSpectralLibrary")] = bool(write_spectral_library)
    if update_spectral_library is not None:
        overrides[(sp, "UpdateSpectralLibrary")] = bool(update_spectral_library)
    overrides.update(normalize_params(params))  # arbitrary passthrough wins
    return Task(task_type="Search", overrides=overrides)


def make_calibration_task(
    *,
    precursor_tol_ppm: float | None = None,
    product_tol_ppm: float | None = None,
    protease: str | None = None,
    max_threads: int | None = None,
    params: dict | None = None,
) -> Task:
    """A ``CalibrationTask`` (produces calibrated ``*-calib.mzML``)."""
    overrides = common_overrides(
        precursor_tol_ppm=precursor_tol_ppm,
        product_tol_ppm=product_tol_ppm,
        protease=protease,
        max_threads=max_threads,
    )
    overrides.update(normalize_params(params))
    return Task(task_type="Calibration", overrides=overrides)


def make_gptmd_task(
    *,
    precursor_tol_ppm: float | None = None,
    product_tol_ppm: float | None = None,
    protease: str | None = None,
    max_threads: int | None = None,
    params: dict | None = None,
) -> Task:
    """A ``GptmdTask`` (produces a PTM-augmented ``*GPTMD.xml`` database)."""
    overrides = common_overrides(
        precursor_tol_ppm=precursor_tol_ppm,
        product_tol_ppm=product_tol_ppm,
        protease=protease,
        max_threads=max_threads,
    )
    overrides.update(normalize_params(params))
    return Task(task_type="Gptmd", overrides=overrides)


def make_glyco_search_task(
    *,
    glyco_search_type: str | None = None,
    precursor_tol_ppm: float | None = None,
    product_tol_ppm: float | None = None,
    protease: str | None = None,
    max_threads: int | None = None,
    params: dict | None = None,
) -> Task:
    """A ``GlycoSearchTask``.

    ``glyco_search_type`` maps to MetaMorpheus's ``GlycoSearchType`` — one of
    ``"OGlycanSearch"``, ``"NGlycanSearch"``, ``"N_O_GlycanSearch"``. None keeps
    the engine default. Glycan databases keep their built-in defaults
    (``OGlycan.gdb`` / ``NGlycan.gdb``) for now.
    """
    overrides = common_overrides(
        precursor_tol_ppm=precursor_tol_ppm,
        product_tol_ppm=product_tol_ppm,
        protease=protease,
        max_threads=max_threads,
    )
    if glyco_search_type is not None:
        overrides[("_glycoSearchParameters", "GlycoSearchType")] = glyco_search_type
    overrides.update(normalize_params(params))
    return Task(task_type="GlycoSearch", overrides=overrides)


def make_xl_search_task(
    *,
    precursor_tol_ppm: float | None = None,
    product_tol_ppm: float | None = None,
    protease: str | None = None,
    max_threads: int | None = None,
    params: dict | None = None,
) -> Task:
    """An ``XLSearchTask`` — cross-link (XL) search.

    Cross-linker-specific settings (e.g. the crosslinker name/masses) live in the
    task's own TOML section; set them via ``params`` or ``available_parameters``.
    """
    overrides = common_overrides(
        precursor_tol_ppm=precursor_tol_ppm,
        product_tol_ppm=product_tol_ppm,
        protease=protease,
        max_threads=max_threads,
    )
    overrides.update(normalize_params(params))
    return Task(task_type="XLSearch", overrides=overrides)


def task_from_toml(toml_path) -> Task:
    """A bring-your-own-TOML task: run this complete task config verbatim.

    The full-fidelity escape hatch — hand it a ``.toml`` you authored or edited
    (e.g. from :func:`available_parameters` or a MetaMorpheus GUI export) and it
    runs exactly as the CLI would, with no generation or patching. Compose with
    :func:`pipeline`, or run directly with :func:`run_toml`.
    """
    return Task(toml_path=Path(toml_path))


# --------------------------------------------------------------------------- #
# Verbs — build a task (or list) and run it.
# --------------------------------------------------------------------------- #

def search(
    spectra,
    database,
    output_dir,
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
    quantify: bool | None = None,
    match_between_runs: bool | None = None,
    normalize: bool | None = None,
    quantify_ppm_tol: float | None = None,
    write_spectral_library: bool | None = None,
    update_spectral_library: bool | None = None,
    params: dict | None = None,
    timeout: float | None = None,
) -> RunResult:
    """Run a classic MetaMorpheus search.

    ``spectra`` is one ``.mzML`` path (or an iterable of them); ``database`` is a
    protein ``.fasta``/``.xml``(``.gz``); ``output_dir`` is where the run
    directory is written. Returns a :class:`RunResult` whose ``.search`` exposes
    ``AllPSMs.psmtsv`` and friends.

    Label-free quantification (FlashLFQ) runs as part of the search and is ON by
    default, so ``result.search.quantified_proteins`` / ``quantified_peptides`` /
    ``quantified_peaks`` are populated. Turn it off with ``quantify=False``, or
    enable match-between-runs with ``match_between_runs=True``.

    Pass ``write_spectral_library=True`` to also generate a ``.msp`` spectral
    library from the confirmed IDs — find it at ``result.search.spectral_library``.

    Any setting not covered by a named argument can be reached through ``params``,
    a ``{section: {key: value}}`` dict applied on top of the generated default —
    see :func:`available_parameters` for the full set. For settings the
    line-patcher can't express, hand a complete config to :func:`run_toml`.
    """
    task = make_search_task(
        precursor_tol_ppm=precursor_tol_ppm,
        product_tol_ppm=product_tol_ppm,
        fixed_mods=fixed_mods,
        variable_mods=variable_mods,
        protease=protease,
        max_missed_cleavages=max_missed_cleavages,
        min_peptide_length=min_peptide_length,
        max_peptide_length=max_peptide_length,
        max_threads=max_threads,
        quantify=quantify,
        match_between_runs=match_between_runs,
        normalize=normalize,
        quantify_ppm_tol=quantify_ppm_tol,
        write_spectral_library=write_spectral_library,
        update_spectral_library=update_spectral_library,
        params=params,
    )
    return run_tasks(
        [task], spectra=spectra, database=database, output_dir=output_dir, timeout=timeout
    )


def calibrate(
    spectra,
    database,
    output_dir,
    *,
    precursor_tol_ppm: float | None = None,
    product_tol_ppm: float | None = None,
    protease: str | None = None,
    max_threads: int | None = None,
    params: dict | None = None,
    timeout: float | None = None,
) -> RunResult:
    """Run a calibration task, producing calibrated ``*-calib.mzML`` spectra
    (``result.calibration.calibrated_spectra``)."""
    task = make_calibration_task(
        precursor_tol_ppm=precursor_tol_ppm,
        product_tol_ppm=product_tol_ppm,
        protease=protease,
        max_threads=max_threads,
        params=params,
    )
    return run_tasks(
        [task], spectra=spectra, database=database, output_dir=output_dir, timeout=timeout
    )


def gptmd(
    spectra,
    database,
    output_dir,
    *,
    precursor_tol_ppm: float | None = None,
    product_tol_ppm: float | None = None,
    protease: str | None = None,
    max_threads: int | None = None,
    params: dict | None = None,
    timeout: float | None = None,
) -> RunResult:
    """Run a GPTMD task, producing a PTM-augmented protein database
    (``result.gptmd.gptmd_database``)."""
    task = make_gptmd_task(
        precursor_tol_ppm=precursor_tol_ppm,
        product_tol_ppm=product_tol_ppm,
        protease=protease,
        max_threads=max_threads,
        params=params,
    )
    return run_tasks(
        [task], spectra=spectra, database=database, output_dir=output_dir, timeout=timeout
    )


def glyco_search(
    spectra,
    database,
    output_dir,
    *,
    glyco_search_type: str | None = None,
    precursor_tol_ppm: float | None = None,
    product_tol_ppm: float | None = None,
    protease: str | None = None,
    max_threads: int | None = None,
    params: dict | None = None,
    timeout: float | None = None,
) -> RunResult:
    """Run a glyco search (``result.glyco_search``)."""
    task = make_glyco_search_task(
        glyco_search_type=glyco_search_type,
        precursor_tol_ppm=precursor_tol_ppm,
        product_tol_ppm=product_tol_ppm,
        protease=protease,
        max_threads=max_threads,
        params=params,
    )
    return run_tasks(
        [task], spectra=spectra, database=database, output_dir=output_dir, timeout=timeout
    )


def xl_search(
    spectra,
    database,
    output_dir,
    *,
    precursor_tol_ppm: float | None = None,
    product_tol_ppm: float | None = None,
    protease: str | None = None,
    max_threads: int | None = None,
    params: dict | None = None,
    timeout: float | None = None,
) -> RunResult:
    """Run a cross-link (XL) search (``result.task("XLSearchTask")``).

    Crosslinker-specific settings go through ``params`` — see
    :func:`available_parameters` with ``"XLSearch"``.
    """
    task = make_xl_search_task(
        precursor_tol_ppm=precursor_tol_ppm,
        product_tol_ppm=product_tol_ppm,
        protease=protease,
        max_threads=max_threads,
        params=params,
    )
    return run_tasks(
        [task], spectra=spectra, database=database, output_dir=output_dir, timeout=timeout
    )


def run_toml(
    toml,
    spectra,
    database,
    output_dir,
    *,
    timeout: float | None = None,
) -> RunResult:
    """Run one or more complete, ready-made task TOMLs verbatim.

    ``toml`` is a path (or an iterable of paths) to task ``.toml`` files — the
    full-fidelity escape hatch for anything the named parameters and ``params``
    passthrough can't express. Equivalent to ``pipeline([task_from_toml(t) ...])``.
    """
    tomls = [toml] if isinstance(toml, (str, Path)) else list(toml)
    tasks = [task_from_toml(t) for t in tomls]
    return run_tasks(
        tasks, spectra=spectra, database=database, output_dir=output_dir, timeout=timeout
    )


def available_parameters(task_type: str = "Search") -> dict[str | None, dict[str, str]]:
    """Return every parameter of a task type as ``{section: {key: default_value}}``.

    Generates the task's default config with ``CMD -g`` and parses it, so what you
    see is exactly what ``params`` can override (same single-line ``key = value``
    model). ``task_type`` is one of ``"Search"``, ``"Calibration"``, ``"Gptmd"``,
    ``"GlycoSearch"``, ``"XLSearch"``.

    Not ``"Averaging"``: ``CMD -g`` writes no ``AveragingTask.toml``, so there are
    no defaults to report and this call would raise. Spectral averaging still runs
    today via :func:`run_toml` with a hand-written config — see ``UPSTREAM.md``
    (U1), which tracks the fix landing in MetaMorpheus itself.

    Example::

        params = pymetamorpheus.available_parameters("Search")
        params["SearchParameters"]["DoParsimony"]       # -> "true"
        # then override any of them:
        mm.search(..., params={"SearchParameters": {"DoParsimony": False}})
    """
    with tempfile.TemporaryDirectory(prefix="pymm_params_") as tmp:
        defaults = generate_default_tomls(Path(tmp))
        name = f"{task_type}Task.toml"
        path = defaults.get(name)
        if path is None:
            raise UsageError(
                f"No such task type {task_type!r}; MetaMorpheus generates: "
                f"{sorted(p[:-len('Task.toml')] for p in defaults)}."
            )
        return read_sections(path)


def pipeline(
    tasks: list[Task],
    spectra,
    database,
    output_dir,
    *,
    timeout: float | None = None,
) -> RunResult:
    """Run several tasks as one MetaMorpheus invocation — the canonical workflow.

    Example (calibrate → GPTMD → search, what ``--test`` does)::

        import pymetamorpheus as mm
        result = mm.pipeline(
            [mm.make_calibration_task(), mm.make_gptmd_task(), mm.make_search_task()],
            spectra="run.mzML", database="proteins.fasta", output_dir="out",
        )

    MetaMorpheus chains the tasks internally — calibration's calibrated spectra
    feed GPTMD, GPTMD's augmented database feeds search. Do NOT try to chain them
    yourself by stringing single-task runs together; that both loses the internal
    hand-off and violates BRIDGE-PARALLELISM (one process, its own threads).
    """
    return run_tasks(
        tasks, spectra=spectra, database=database, output_dir=output_dir, timeout=timeout
    )
