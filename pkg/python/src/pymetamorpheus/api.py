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

from ._engine import Task, common_overrides, run_tasks
from .results import RunResult

__all__ = [
    "search",
    "calibrate",
    "gptmd",
    "glyco_search",
    "pipeline",
    "Task",
    "make_search_task",
    "make_calibration_task",
    "make_gptmd_task",
    "make_glyco_search_task",
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
) -> Task:
    """A classic ``SearchTask`` with the common parameters overridden.

    Quantification (FlashLFQ) is part of the search task and is ON by default in
    MetaMorpheus, producing ``AllQuantifiedProteinGroups.tsv`` /
    ``AllQuantifiedPeptides.tsv`` / ``AllQuantifiedPeaks.tsv``. The quant knobs
    below map to ``[SearchParameters]``; leave them None to keep MetaMorpheus's
    defaults.
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
    return Task(task_type="Search", overrides=overrides)


def make_calibration_task(
    *,
    precursor_tol_ppm: float | None = None,
    product_tol_ppm: float | None = None,
    protease: str | None = None,
    max_threads: int | None = None,
) -> Task:
    """A ``CalibrationTask`` (produces calibrated ``*-calib.mzML``)."""
    return Task(
        task_type="Calibration",
        overrides=common_overrides(
            precursor_tol_ppm=precursor_tol_ppm,
            product_tol_ppm=product_tol_ppm,
            protease=protease,
            max_threads=max_threads,
        ),
    )


def make_gptmd_task(
    *,
    precursor_tol_ppm: float | None = None,
    product_tol_ppm: float | None = None,
    protease: str | None = None,
    max_threads: int | None = None,
) -> Task:
    """A ``GptmdTask`` (produces a PTM-augmented ``*GPTMD.xml`` database)."""
    return Task(
        task_type="Gptmd",
        overrides=common_overrides(
            precursor_tol_ppm=precursor_tol_ppm,
            product_tol_ppm=product_tol_ppm,
            protease=protease,
            max_threads=max_threads,
        ),
    )


def make_glyco_search_task(
    *,
    glyco_search_type: str | None = None,
    precursor_tol_ppm: float | None = None,
    product_tol_ppm: float | None = None,
    protease: str | None = None,
    max_threads: int | None = None,
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
    return Task(task_type="GlycoSearch", overrides=overrides)


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
    timeout: float | None = None,
) -> RunResult:
    """Run a calibration task, producing calibrated ``*-calib.mzML`` spectra
    (``result.calibration.calibrated_spectra``)."""
    task = make_calibration_task(
        precursor_tol_ppm=precursor_tol_ppm,
        product_tol_ppm=product_tol_ppm,
        protease=protease,
        max_threads=max_threads,
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
    timeout: float | None = None,
) -> RunResult:
    """Run a GPTMD task, producing a PTM-augmented protein database
    (``result.gptmd.gptmd_database``)."""
    task = make_gptmd_task(
        precursor_tol_ppm=precursor_tol_ppm,
        product_tol_ppm=product_tol_ppm,
        protease=protease,
        max_threads=max_threads,
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
    timeout: float | None = None,
) -> RunResult:
    """Run a glyco search (``result.glyco_search``)."""
    task = make_glyco_search_task(
        glyco_search_type=glyco_search_type,
        precursor_tol_ppm=precursor_tol_ppm,
        product_tol_ppm=product_tol_ppm,
        protease=protease,
        max_threads=max_threads,
    )
    return run_tasks(
        [task], spectra=spectra, database=database, output_dir=output_dir, timeout=timeout
    )


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
