# Changelog

All notable changes to pyMetaMorpheus are recorded here. Format loosely follows
[Keep a Changelog](https://keepachangelog.com/); versions follow semver.

## [Unreleased]

## [0.0.2.dev0]

The first tag this project has ever cut, and deliberately a dev preview: its purpose is to exercise
the release path end to end rather than to ship anything. `PYPI_PUBLISH` is unset, so it builds,
tests and attaches a wheel to a GitHub prerelease and touches no public index.

### Added — release and upstream automation
- **The MetaMorpheus pin is machine-readable.** `code/metamorpheus.pin` holds the commit, one copy;
  `publish-runner.ps1` refuses a checkout that is at a different commit, and CI fetches exactly that
  commit.
- **`upstream-watch.yml`** — weekly, opens a pull request bumping the pin when MetaMorpheus cuts a
  release that is genuinely *ahead* of it. Never pushes: the bump PR runs the live canary, which is
  what makes the bump trustworthy.
- **`release.yml`** — a `v*` tag checks the tag against the declared version, runs the whole CI
  matrix (called, not duplicated), builds the wheel and attaches it to the GitHub Release. PyPI
  publishing is wired behind the `PYPI_PUBLISH` repository variable and switched off.
- **One version source** — `__version__` in `__init__.py`, with hatchling deriving the distribution
  metadata from it.
- **A test that keeps the READMEs honest** — every capability in `__all__` must appear on the repo
  README, the PyPI README and the docs landing page.

### Fixed
- **CI's live canary was building MetaMorpheus `master`, not the pin.** The wheel projected a July
  commit while the canary tested whatever upstream happened to be that morning, so a green tick said
  nothing about the build users would actually get.
- **Five capabilities were missing from every page a stranger reads first** — `xl_search`,
  `run_toml`, `available_parameters`, label-free quantification and spectral-library generation were
  documented in the guides and absent from all three landing surfaces.
- **A stale caveat below claimed cross-link search was not exposed**, three bullets under the entry
  announcing that it was.

## [0.0.1]

### Added
- **Classic search vignette** — `search(spectra, database, output_dir, ...)` runs a MetaMorpheus
  classic search and returns a typed `RunResult` (`result.search.all_psms`, etc.).
- **Label-free quantification (FlashLFQ)** — runs as part of the search (on by default). New
  `search()` knobs `quantify`, `match_between_runs`, `normalize`, `quantify_ppm_tol`, and result
  accessors `quantified_proteins` / `quantified_peptides` / `quantified_peaks`
  (`AllQuantified*.tsv`).
- **Spectral library generation** — `search(..., write_spectral_library=True)` emits a `.msp`
  spectral library from the confirmed IDs (`update_spectral_library` to update an existing one);
  exposed as `result.search.spectral_library`.
- **Full parameter access across every task** — three complementary levels so no setting is out of
  reach: (1) named arguments for common knobs; (2) `params={section: {key: value}}` arbitrary
  passthrough on every verb/builder, validated against the real schema (typos error loudly); (3)
  `run_toml(...)` / `task_from_toml(...)` to run a complete hand-authored config verbatim. Plus
  `available_parameters(task_type)` to introspect the full default config (Search ~112, Calibration
  ~73, Gptmd ~69, GlycoSearch ~95, XLSearch ~87 settings).
- **Cross-link search exposed** — `xl_search()` / `make_xl_search_task()` (`XLSearchTask`), completing
  coverage of all five task types MetaMorpheus generates.

### Fixed
- **CI/packaging**: `pkg/build/publish-runner.ps1` was being swallowed by a too-broad `build/`
  gitignore rule (now anchored to `pkg/python/build/`), which broke the live CI job. Enabled
  `tool.hatch.metadata.allow-direct-references` so the `[pymzlib]` git extra passes hatchling's
  metadata validation (the offline CI jobs failed to `pip install` without it).
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
- **Docs** — MkDocs site: getting-started (zero → first result), getting-your-data (fetch spectra
  from PRIDE and databases from UniProt via pyMzLib), classic search, tasks/pipelines, full parameter
  access, results (how to actually read your output — stdlib / pandas / pyMzLib, plus the run summary
  and methods prose), installation. New `summary` / `prose` result accessors (`results.txt`,
  `AutoGeneratedManuscriptProse.txt`). Builds clean under `mkdocs build --strict`; `[docs]` extra added.
- **Auto-generated API reference** via mkdocstrings (`docs/reference.md`) covering every public verb,
  task builder, result type, and error — rendered from the source docstrings.
- **Published documentation site** — a `docs` GitHub Actions workflow builds and deploys to GitHub
  Pages on every push to `main` (https://smith-chem-wisc.github.io/pyMetaMorpheus/).
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
  during long runs.
