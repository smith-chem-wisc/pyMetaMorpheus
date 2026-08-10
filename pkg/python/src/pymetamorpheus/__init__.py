"""pyMetaMorpheus — MetaMorpheus, callable from Python.

MetaMorpheus is a mass-spectrometry proteomics search engine (calibration, GPTMD,
peptide/protein search, glyco search) built by the Smith lab on top of mzLib. It
already ships a command line, so this package is a thin, **dependency-free**,
faithful projection of that CLI — it writes the TOML task config, invokes the CLI
non-interactively, and surfaces the resulting run directory as typed results. It
reimplements no search logic.

Quick start::

    import pymetamorpheus as mm

    result = mm.search(
        spectra="myrun.mzML",
        database="proteins.fasta",
        output_dir="out",
        precursor_tol_ppm=5,
        product_tol_ppm=20,
    )
    print(result.search.all_psms)        # -> out/Task1SearchTask/AllPSMs.psmtsv

The canonical multi-task workflow (calibrate → GPTMD → search)::

    result = mm.pipeline(
        [mm.make_calibration_task(), mm.make_gptmd_task(), mm.make_search_task()],
        spectra="myrun.mzML", database="proteins.fasta", output_dir="out",
    )

Notes
-----
* Input is currently ``.mzML`` only (``.raw`` support is deferred until the
  Thermo license can be accepted non-interactively — gap G-settings).
* Outputs are standard mzLib result files (TSV / mzID). For parsed tables,
  compose with pyMzLib's readers rather than re-parsing here.
* The MetaMorpheus CLI is located via the ``PYMM_METAMORPHEUS`` environment
  variable or a self-contained payload staged into the wheel.
"""

from __future__ import annotations

from ._errors import (
    MetaMorpheusNotFoundError,
    PyMetaMorpheusError,
    RunError,
    UsageError,
)
from .api import (
    Task,
    available_parameters,
    calibrate,
    glyco_search,
    gptmd,
    make_calibration_task,
    make_glyco_search_task,
    make_gptmd_task,
    make_search_task,
    make_xl_search_task,
    pipeline,
    run_toml,
    search,
    task_from_toml,
    xl_search,
)
from .results import RunResult, TaskResult

__version__ = "0.0.2.dev0"

__all__ = [
    "__version__",
    # verbs
    "search",
    "calibrate",
    "gptmd",
    "glyco_search",
    "xl_search",
    "pipeline",
    "run_toml",
    # introspection
    "available_parameters",
    # task builders
    "Task",
    "make_search_task",
    "make_calibration_task",
    "make_gptmd_task",
    "make_glyco_search_task",
    "make_xl_search_task",
    "task_from_toml",
    # results
    "RunResult",
    "TaskResult",
    # errors
    "PyMetaMorpheusError",
    "UsageError",
    "RunError",
    "MetaMorpheusNotFoundError",
]
