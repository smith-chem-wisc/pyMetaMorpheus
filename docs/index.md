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
- **Every task type is the same code path.** `calibrate`, `gptmd`, `search`, `glyco_search`,
  `xl_search` and multi-task `pipeline` differ only in which TOML gets patched.
- **Outputs are standard mzLib result files** (TSV / mzID). For parsed tables, compose with
  [pyMzLib](https://github.com/smith-chem-wisc/pyMzLib)'s readers — don't re-parse.

## What it can do

| capability | call | notes |
|---|---|---|
| calibration | `mm.calibrate(...)` | → `*-calib.mzML` |
| GPTMD | `mm.gptmd(...)` | → `*GPTMD.xml`, a PTM-augmented database |
| peptide/protein search | `mm.search(...)` | → `AllPSMs.psmtsv`, `AllPeptides.psmtsv`, … |
| glyco search | `mm.glyco_search(...)` | N- and O-glycan |
| cross-link search | `mm.xl_search(...)` | XLSearchTask |
| multi-task pipeline | `mm.pipeline([...])` | several tasks, **one** CLI invocation |
| label-free quantification | `quantify=True` on `search` | FlashLFQ, part of the search task and **on by default** |
| spectral library generation | `write_spectral_library=True` on `search` | off by default; `update_spectral_library=` extends one |
| run a hand-written TOML | `mm.run_toml(...)` | anything the exposed surface does not reach |
| discover every parameter | `mm.available_parameters("Search")` | what MetaMorpheus itself offers for a task type |

The last two rows matter more than their size suggests: the named arguments on each verb are a
curated subset, and those two calls are how you reach everything else without leaving Python. See
[Full parameter access](guides/full-access.md).

## Next

- **[Getting started](guides/getting-started.md)** — zero to your first identified peptides.
- [Getting your data (PRIDE & UniProt)](guides/getting-data.md) — fetch spectra and databases in Python.
- [Classic search](guides/search.md)
- [Calibration, GPTMD, glyco & pipelines](guides/tasks.md)
- [Full parameter access](guides/full-access.md)
- [Results — finding and reading your output](guides/results.md)
- [Installation & locating the CLI](guides/installation.md)
