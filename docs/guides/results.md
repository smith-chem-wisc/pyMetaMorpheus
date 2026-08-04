# Results & output files

Every verb returns a `RunResult`. A run's output directory contains one subfolder per task, named
`Task<N><TaskType>` (e.g. `Task1SearchTask`, `Task2GptmdTask`), and `RunResult` gives you typed
access to them.

```python
result = mm.search("myrun.mzML", "proteins.fasta", "out")

result.output_dir          # Path("out")
result.tasks               # [TaskResult(index=1, task_type="SearchTask", ...)]
result.search              # the SearchTask TaskResult (or None)
result.calibration         # the CalibrationTask TaskResult (or None)
result.gptmd               # the GptmdTask TaskResult (or None)
result.glyco_search        # the GlycoSearchTask TaskResult (or None)
result.task("SearchTask")  # look up any task type by name
```

## `TaskResult`

Each `TaskResult` points at one task's output folder and offers path accessors that return `None`
when the file isn't present (so you can duck-type across task types):

| accessor | file |
|---|---|
| `all_psms` | `AllPSMs.psmtsv` |
| `all_peptides` | `AllPeptides.psmtsv` |
| `all_proteins` / `quantified_proteins` | `AllQuantifiedProteinGroups.tsv` |
| `quantified_peptides` | `AllQuantifiedPeptides.tsv` |
| `quantified_peaks` | `AllQuantifiedPeaks.tsv` |
| `spectral_library` | `*.msp` (when `write_spectral_library=True`) |
| `mzid` | `*.mzID` |
| `calibrated_spectra` | `*-calib.mzML` |
| `gptmd_database` | `*GPTMD.xml` |
| `glyco_psms` | `*.psmtsv` |

For anything else, use `.file("SomeName.tsv")` or `.glob("*.tsv")` on the task's `.directory`.

## The files are mzLib result files — read them with pyMzLib

pyMetaMorpheus returns **paths**, not parsed tables. That is deliberate: the outputs are standard
mzLib result files, and [pyMzLib](https://github.com/smith-chem-wisc/pyMzLib) already parses them.
Re-parsing here would duplicate that work and drift from the format the mainland owns.

To get rich, typed tables, compose the two bindings:

```python
import pymetamorpheus as mm
import pymzlib

result = mm.search("myrun.mzML", "proteins.fasta", "out")
# pyMetaMorpheus accessors return pathlib.Path; pyMzLib's readers currently
# expect a string, so wrap with str(...).
psms = pymzlib.readers.read_results(str(result.search.all_psms))   # parsed by pyMzLib
```

Install the optional extra to pull pyMzLib in alongside pyMetaMorpheus:

```bash
pip install "pymetamorpheus[pymzlib]"
```

!!! note "pyMzLib isn't on PyPI yet"
    Until the Smith-lab pyMzLib is published to PyPI, the `[pymzlib]` extra installs
    it from source over git (see the extra in `pyproject.toml`). Do **not** run
    `pip install pymzlib` on its own — an unrelated package of the same name exists
    on PyPI. This resolves once pyMzLib is published (tracked with gap G-dist).

!!! note "TSV, not CSV"
    MetaMorpheus writes tab-separated values. pyMetaMorpheus surfaces those files as-is — no
    reformatting.
