# Classic search

The `search` verb runs a classic MetaMorpheus peptide/protein search: spectra in, a protein database
in, a run directory out.

```python
import pymetamorpheus as mm

result = mm.search(
    spectra="myrun.mzML",
    database="proteins.fasta",
    output_dir="out",
    precursor_tol_ppm=5,
    product_tol_ppm=20,
    variable_mods=["Common Variable|Oxidation on M"],
    max_threads=8,
)

search = result.search                 # a TaskResult
print(search.directory)                # out/Task1SearchTask
print(search.all_psms)                 # .../AllPSMs.psmtsv
print(search.all_peptides)             # .../AllPeptides.psmtsv
print(search.all_proteins)             # .../AllQuantifiedProteinGroups.tsv
```

## Inputs

| argument | meaning |
|---|---|
| `spectra` | one `.mzML` path, or an iterable of them |
| `database` | a protein database: `.fasta`/`.fa`, `.xml` (UniProt), or a `.gz` of either |
| `output_dir` | where the run directory is written (created if absent) |

!!! note "mzML only, for now"
    pyMetaMorpheus currently accepts `.mzML` input. `.raw` is rejected early, before any process is
    spawned, because a `.raw` run hangs on the Thermo license prompt until that is accepted
    non-interactively. Convert `.raw` with MSConvert, or export `.mzML` from your instrument.

## Parameters

Every parameter is optional; anything you leave out keeps MetaMorpheus's own default (from
`CMD -g`). The surface is deliberately small — the knobs an investigator reaches for first:

| parameter | MetaMorpheus setting |
|---|---|
| `precursor_tol_ppm` | `PrecursorMassTolerance` |
| `product_tol_ppm` | `ProductMassTolerance` |
| `fixed_mods` | `ListOfModsFixed` |
| `variable_mods` | `ListOfModsVariable` |
| `protease` | `Protease` / `SpecificProtease` |
| `max_missed_cleavages` | `MaxMissedCleavages` |
| `min_peptide_length` / `max_peptide_length` | `MinPeptideLength` / `MaxPeptideLength` |
| `max_threads` | `MaxThreadsToUsePerFile` |

### Modifications

Modifications are given as `"Category|Name"` strings and translated to MetaMorpheus's tab-delimited
`ListOfMods*` form for you:

```python
mm.search(
    spectra, database, "out",
    fixed_mods=["Common Fixed|Carbamidomethyl on C"],
    variable_mods=["Common Variable|Oxidation on M", "Common Variable|Acetylation on X"],
)
```

### A word on threads

`max_threads` maps straight to MetaMorpheus's own `MaxThreadsToUsePerFile`. pyMetaMorpheus never
launches multiple CLI runs in parallel to "go faster" — MetaMorpheus parallelizes **within** one
process, and its thread count is a correctness surface, not just a speed knob. One run, its own
threads.
