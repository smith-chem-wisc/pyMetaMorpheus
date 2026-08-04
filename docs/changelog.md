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

### Hardening (from a four-auditor review)
- CLI is located **before** the output directory is created, so a missing MetaMorpheus no longer
  leaves an empty output folder behind.
- Malformed modification strings now raise `UsageError` (a `PyMetaMorpheusError`), not a bare
  `ValueError` — every bad-input case is catchable under one hierarchy.
- TOML patching genuinely **preserves the source newline style** (CRLF stays CRLF, LF stays LF)
  instead of rewriting to the platform default.
- A run that exits 0 but produces **no expected task folder** now fails loudly with `RunError`
  instead of returning a silent empty result.
- Subprocess output is decoded as **UTF-8** (not the OS locale codepage), so `±` and non-ASCII
  names in MetaMorpheus output can't raise an untyped `UnicodeDecodeError`.
- A `.gz` database must wrap a `.fasta`/`.fa`/`.xml` (a bare `foo.gz` is rejected).
- `[pymzlib]` extra points at pyMzLib by VCS (it isn't on PyPI, and a same-named unrelated package
  is) — provisional until pyMzLib is published; docs updated with `str(...)` around the pyMzLib
  composition example.

### Notes
- Verified end-to-end through the Python API against MetaMorpheus's bundled
  `SmallCalibratible_Yeast.mzML` + `SmallYeast.fasta` (89 PSMs), and independently on **real 227 MB
  human PRIDE data (PXD008952) fetched via pyMzLib** against UniProt human Swiss-Prot (15,796 PSMs).
- Results are standard mzLib files — parse them by composing with pyMzLib, not by re-parsing here.
- Known limitations (by design): `.mzML` only (`.raw` deferred, G-settings); no progress streaming
  during long runs; cross-link search (`XLSearchTask`) not yet exposed.
