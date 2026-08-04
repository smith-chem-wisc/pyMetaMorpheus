# Changelog

All notable changes to pyMetaMorpheus are recorded here. Format loosely follows
[Keep a Changelog](https://keepachangelog.com/); versions follow semver.

## [Unreleased]

### Added
- **Classic search vignette** — `search(spectra, database, output_dir, ...)` runs a MetaMorpheus
  classic search and returns a typed `RunResult` (`result.search.all_psms`, etc.).
- **All four task types** as sibling verbs on the shared engine: `calibrate` (CalibrationTask),
  `gptmd` (GptmdTask), `search` (SearchTask), `glyco_search` (GlycoSearchTask).
- **`pipeline([...tasks], ...)`** — run several tasks in one MetaMorpheus invocation (the canonical
  calibrate → GPTMD → search workflow); tasks chain internally.
- **Task builders** (`make_search_task`, `make_calibration_task`, `make_gptmd_task`,
  `make_glyco_search_task`) for composing custom pipelines.
- **Dependency-free TOML patching** — generate each task's default config via `CMD -g`, then
  section-aware line-patch only the exposed parameters; no third-party TOML library.
- **mzML-only input validation** — `.raw` is rejected early with a clear message (Thermo license is
  deferred, gap G-settings).
- **Typed results** — `RunResult` / `TaskResult` discover `TaskN<Type>` output folders and expose
  path accessors (`all_psms`, `all_peptides`, `calibrated_spectra`, `gptmd_database`, `glyco_psms`).
- **CLI location** via `PYMM_METAMORPHEUS` env var or a staged self-contained payload; a clear
  `MetaMorpheusNotFoundError` when neither is present.
- **Tests** — 18 offline unit tests (TOML patching, validation, result discovery) + a live canary
  (`pytest -m live`) that runs a real search and calibration.
- **Docs** — MkDocs site: search, tasks/pipelines, results, installation.
- **Zero-dependency packaging** (`pyproject.toml`, hatchling), optional extras `[pymzlib]`,
  `[pandas]`, `[dev]`.

### Notes
- Verified end-to-end through the Python API against MetaMorpheus's bundled
  `SmallCalibratible_Yeast.mzML` + `SmallYeast.fasta` (89 PSMs).
- Results are standard mzLib files — parse them by composing with pyMzLib, not by re-parsing here.
