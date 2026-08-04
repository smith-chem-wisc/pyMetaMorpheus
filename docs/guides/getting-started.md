# Getting started

This walks you from nothing to your first identified peptides in about five minutes. Follow it top to
bottom.

## What you need

- **Python 3.9+**.
- **A MetaMorpheus command-line build.** pyMetaMorpheus drives the MetaMorpheus CLI. While the
  self-contained wheel is being finalized (gap G-dist), you point it at a MetaMorpheus build you
  already have — see [step 2](#step-2-point-at-a-metamorpheus-cli).

You do **not** need .NET knowledge, and you don't write any C#.

## Step 1 — install pyMetaMorpheus

pyMetaMorpheus isn't on PyPI yet, so install it from source. It has **zero required dependencies**, so
this is quick:

```bash
git clone https://github.com/smith-chem-wisc/pyMetaMorpheus.git
cd pyMetaMorpheus
python -m pip install -e pkg/python           # add "[pandas]" for nicer result tables
```

Check it imports:

```bash
python -c "import pymetamorpheus as mm; print(mm.__version__)"
```

## Step 2 — point at a MetaMorpheus CLI

Set the `PYMM_METAMORPHEUS` environment variable to the MetaMorpheus `CMD` executable (or the folder
containing it). If you have a MetaMorpheus checkout that you've built:

=== "Windows (PowerShell)"

    ```powershell
    $env:PYMM_METAMORPHEUS = "C:\path\to\MetaMorpheus\CMD\bin\Release\net8.0\CMD.exe"
    ```

=== "Linux / macOS"

    ```bash
    export PYMM_METAMORPHEUS=/path/to/CMD          # native build, or .../CMD.dll for a framework build
    ```

Don't have a build? Grab a MetaMorpheus release, or build the CLI once with
`dotnet build MetaMorpheus/CMD` from a [MetaMorpheus](https://github.com/smith-chem-wisc/MetaMorpheus)
checkout. If pyMetaMorpheus can't find it, it tells you exactly where it looked and names this
variable.

## Step 3 — get a bit of data

You need one **`.mzML`** spectra file and one protein **`.fasta`** (or UniProt `.xml`). A MetaMorpheus
checkout ships a tiny example under `MetaMorpheus/EngineLayer/Data/`:
`SmallCalibratible_Yeast.mzML` and `SmallYeast.fasta`. Use those, or your own.

Don't have data handy? You can fetch spectra from PRIDE and a protein database from UniProt straight
from Python with pyMzLib — see **[Getting your data](getting-data.md)**.

!!! note "`.mzML` only for now"
    pyMetaMorpheus currently accepts `.mzML`. If you have `.raw`, convert it with MSConvert or export
    `.mzML` from your instrument software (`.raw` support is deferred — gap G-settings).

## Step 4 — run your first search

```python
import pymetamorpheus as mm

result = mm.search(
    spectra="SmallCalibratible_Yeast.mzML",
    database="SmallYeast.fasta",
    output_dir="my_first_run",
    precursor_tol_ppm=5,
    product_tol_ppm=20,
)
print("done:", result.search.directory)
```

## Step 5 — look at what you got

Read the human-readable summary first, then count your confident IDs:

```python
# 1. MetaMorpheus's own summary — ID counts, FDR, settings used
print(result.search.summary.read_text(encoding="utf-8"))

# 2. Count identified peptides at 1% FDR (needs pandas: pip install "pymetamorpheus[pandas]")
import pandas as pd
peptides = pd.read_csv(result.search.all_peptides, sep="\t")
print(len(peptides[peptides["QValue"] <= 0.01]), "peptides at q ≤ 0.01")
```

No pandas? The [Results guide](results.md) shows the same thing with only the standard library.

## Where to go next

- **[Classic search](search.md)** — all the search knobs (tolerances, mods, protease, quantification,
  spectral libraries).
- **[Calibration, GPTMD, glyco & pipelines](tasks.md)** — the other task types and how to chain them.
- **[Full parameter access](full-access.md)** — reach *any* MetaMorpheus setting, not just the named
  ones.
- **[Results](results.md)** — everything about finding and reading your output.

## Troubleshooting

| symptom | cause / fix |
|---|---|
| `MetaMorpheusNotFoundError` | `PYMM_METAMORPHEUS` isn't set or points at the wrong place. The error lists every path it tried. |
| `UsageError: Unsupported spectra format '.raw'` | Convert to `.mzML` (see step 3). |
| `UsageError: ... no matching key ...` | A `params` section/key is misspelled — check with `mm.available_parameters("Search")`. |
| `RunError: MetaMorpheus exited with code …` | The engine itself failed; the message includes its stdout/stderr tail. |
| the call seems to hang | A very large search can take a while; pass a `timeout=` (seconds) to fail fast instead of waiting. |
