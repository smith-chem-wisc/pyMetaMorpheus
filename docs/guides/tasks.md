# Calibration, GPTMD, glyco search & pipelines

Every MetaMorpheus task is the same machinery — generate the default TOML, patch a few parameters,
run — so the verbs are siblings of `search`.

## Calibration

Recalibrates the m/z axis, writing calibrated `*-calib.mzML` spectra you can feed to a later task.

```python
result = mm.calibrate("myrun.mzML", "proteins.fasta", "out")
calibrated = result.calibration.calibrated_spectra   # [Path(".../myrun-calib.mzML")]
```

## GPTMD

The **G**lobal **P**ost-**T**ranslational **M**odification **D**iscovery task augments your protein
database with modifications it finds, writing a `*GPTMD.xml` you can search against.

```python
result = mm.gptmd("myrun.mzML", "proteins.fasta", "out")
augmented_db = result.gptmd.gptmd_database            # [Path(".../proteinsGPTMD.xml")]
```

## Glyco search

```python
result = mm.glyco_search(
    "myrun.mzML", "proteins.fasta", "out",
    glyco_search_type="NGlycanSearch",   # or "OGlycanSearch", "N_O_GlycanSearch"
)
psms = result.glyco_search.glyco_psms
```

`glyco_search_type` maps to MetaMorpheus's `GlycoSearchType`. The glycan databases keep their
built-in defaults (`OGlycan.gdb` / `NGlycan.gdb`).

## Pipelines — the canonical workflow

The standard MetaMorpheus workflow is **calibrate → GPTMD → search**, run as a single invocation.
MetaMorpheus chains the tasks *internally*: calibration's calibrated spectra feed GPTMD, GPTMD's
augmented database feeds search. Run them together with `pipeline`:

```python
result = mm.pipeline(
    [mm.make_calibration_task(), mm.make_gptmd_task(), mm.make_search_task()],
    spectra="myrun.mzML",
    database="proteins.fasta",
    output_dir="out",
)

for task in result.tasks:
    print(task.index, task.task_type, task.directory)
# 1 CalibrationTask  out/Task1CalibrationTask
# 2 GptmdTask        out/Task2GptmdTask
# 3 SearchTask       out/Task3SearchTask
```

!!! warning "Don't chain tasks yourself"
    It is tempting to call `calibrate(...)`, then feed its output to `gptmd(...)`, then to
    `search(...)`. Don't. That loses MetaMorpheus's internal hand-off and launches three processes
    where one is correct (and correct for thread accounting). Build a task list and pass it to
    `pipeline`.

## Task builders

`make_search_task`, `make_calibration_task`, `make_gptmd_task`, and `make_glyco_search_task` accept
the same parameters as their verb counterparts but *return* a `Task` without running it, so you can
compose custom pipelines — e.g. a GPTMD run followed by two searches with different tolerances:

```python
tasks = [
    mm.make_gptmd_task(precursor_tol_ppm=10),
    mm.make_search_task(precursor_tol_ppm=5),
    mm.make_search_task(precursor_tol_ppm=20),
]
mm.pipeline(tasks, spectra="myrun.mzML", database="proteins.fasta", output_dir="out")
```
