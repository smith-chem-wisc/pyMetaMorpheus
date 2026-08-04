# pyMetaMorpheus

**MetaMorpheus, callable from Python — with zero dependency friction.**

[MetaMorpheus](https://github.com/smith-chem-wisc/MetaMorpheus) is a mass-spectrometry
proteomics search engine (calibration, GPTMD, peptide/protein search, glyco search) built by the
Smith lab on top of [mzLib](https://github.com/smith-chem-wisc/mzLib). It already ships a command
line, so **pyMetaMorpheus is a thin, dependency-free, faithful projection of that CLI** — it writes
the TOML task config, invokes the CLI non-interactively, and surfaces the resulting run directory as
typed Python results. It reimplements no search logic.

## Why it's shaped this way

MetaMorpheus is an *application* with an existing command line, so — unlike a library binding —
**there is no bridge to build.** The CLI's `TOML task + input files → output run directory`
interface is already language-neutral, which makes pyMetaMorpheus small and honest:

- **Zero third-party Python runtime dependencies.** The wheel carries (or fetches) a self-contained
  MetaMorpheus CLI; you don't install .NET, and you don't manage a version handshake.
- **Faithful projection, never a repair site.** If MetaMorpheus behaves a certain way, so do we. Bugs
  get fixed upstream in MetaMorpheus, not patched over in Python.
- **The outputs are standard mzLib result files.** For parsed tables, compose with
  [pyMzLib](https://github.com/smith-chem-wisc/pyMzLib)'s readers rather than re-parsing here.

## Quick start

```python
import pymetamorpheus as mm

result = mm.search(
    spectra="myrun.mzML",
    database="proteins.fasta",
    output_dir="out",
    precursor_tol_ppm=5,
    product_tol_ppm=20,
    variable_mods=["Common Variable|Oxidation on M"],
)

print(result.search.all_psms)   # -> out/Task1SearchTask/AllPSMs.psmtsv
```

### The four task types

```python
mm.calibrate(spectra, database, "out")       # -> *-calib.mzML
mm.gptmd(spectra, database, "out")           # -> *GPTMD.xml (PTM-augmented DB)
mm.search(spectra, database, "out")          # -> AllPSMs.psmtsv, AllPeptides.psmtsv, ...
mm.glyco_search(spectra, database, "out", glyco_search_type="NGlycanSearch")
```

### The canonical pipeline (calibrate → GPTMD → search)

MetaMorpheus chains tasks *internally* — calibration's calibrated spectra feed GPTMD, GPTMD's
augmented database feeds search — so you run them as **one** invocation, not three:

```python
result = mm.pipeline(
    [mm.make_calibration_task(), mm.make_gptmd_task(), mm.make_search_task()],
    spectra="myrun.mzML", database="proteins.fasta", output_dir="out",
)
for task in result.tasks:
    print(task.index, task.task_type, task.directory)
```

## Current limitations

- **Input is `.mzML` only** for now. `.raw` support is deferred until the Thermo license can be
  accepted non-interactively. Convert `.raw` with MSConvert, or export `.mzML` from your instrument.
- The exposed parameter surface is intentionally small (the knobs reached for first). Everything else
  keeps MetaMorpheus's own defaults; the surface widens on demand, not speculatively.

## Locating the CLI

The runner finds MetaMorpheus via, in order:

1. `PYMM_METAMORPHEUS` — path to `CMD.exe`/`CMD.dll` or the folder containing it (dev + CI).
2. A self-contained payload staged inside the installed wheel.

## Development

```bash
python -m venv .venv && .venv/Scripts/pip install -e ".[dev]"
.venv/Scripts/pytest -m "not live"     # offline suite (no CLI needed)
PYMM_METAMORPHEUS=/path/to/CMD.exe .venv/Scripts/pytest -m live   # live canary
```

## License

MIT (this binding). MetaMorpheus and mzLib carry their own licenses.
