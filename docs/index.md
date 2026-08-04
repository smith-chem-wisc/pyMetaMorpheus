# pyMetaMorpheus

**MetaMorpheus, callable from Python — with zero dependency friction.**

[MetaMorpheus](https://github.com/smith-chem-wisc/MetaMorpheus) is a mass-spectrometry proteomics
search engine (calibration, GPTMD, peptide/protein search, glyco search) built by the Smith lab on
top of [mzLib](https://github.com/smith-chem-wisc/mzLib). It already ships a command line, so
**pyMetaMorpheus is a thin, dependency-free, faithful projection of that CLI**.

```python
import pymetamorpheus as mm

result = mm.search(
    spectra="myrun.mzML",
    database="proteins.fasta",
    output_dir="out",
    precursor_tol_ppm=5,
    product_tol_ppm=20,
)
print(result.search.all_psms)   # -> out/Task1SearchTask/AllPSMs.psmtsv
```

## The one idea to internalize

MetaMorpheus is an **application with an existing CLI**, so — unlike a library binding such as
pyMzLib — **there is no bridge to build.** The CLI's `TOML task + input files → output run directory`
interface is already language-neutral. pyMetaMorpheus:

1. generates the current default TOML for each task straight from MetaMorpheus (`CMD -g`),
2. surgically patches only the handful of parameters it exposes,
3. hands the whole task list to **one** CLI invocation, and
4. surfaces the run directory as typed results.

It reimplements no search logic and repairs nothing in Python. If MetaMorpheus has a bug, it is fixed
upstream in MetaMorpheus — pyMetaMorpheus discloses an honest caveat meanwhile, never a silent
work-around.

## What this buys you

- **Zero third-party Python runtime dependencies.** The wheel carries (or fetches) a self-contained
  MetaMorpheus CLI. No .NET install, no version handshake.
- **Every task type is the same code path.** `calibrate`, `gptmd`, `search`, `glyco_search`, and
  multi-task `pipeline` differ only in which TOML gets patched.
- **Outputs are standard mzLib result files** (TSV / mzID). For parsed tables, compose with
  [pyMzLib](https://github.com/smith-chem-wisc/pyMzLib)'s readers — don't re-parse.

## Next

- **[Getting started](guides/getting-started.md)** — zero to your first identified peptides.
- [Getting your data (PRIDE & UniProt)](guides/getting-data.md) — fetch spectra and databases in Python.
- [Classic search](guides/search.md)
- [Calibration, GPTMD, glyco & pipelines](guides/tasks.md)
- [Full parameter access](guides/full-access.md)
- [Results — finding and reading your output](guides/results.md)
- [Installation & locating the CLI](guides/installation.md)
