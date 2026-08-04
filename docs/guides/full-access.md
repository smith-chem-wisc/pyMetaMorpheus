# Full parameter access

The named arguments on `search`, `calibrate`, `gptmd`, `glyco_search`, and `xl_search` cover the knobs
reached for most often. But MetaMorpheus tasks have **dozens to a hundred-plus** settings each, and the
project's whole premise is that the TOML *is* the complete interface. So every setting is reachable —
you never have to wait for a wrapper to add a named argument.

There are three levels, from most convenient to most complete.

## 1. Named arguments

The ergonomic common cases, e.g. `search(spectra, db, out, precursor_tol_ppm=5, quantify=False)`. See
the [search guide](search.md) and [tasks guide](tasks.md).

## 2. `params=` — arbitrary passthrough

Any setting, named or not, can be overridden with a `params` dict shaped like the TOML itself —
`{section: {key: value}}`. It's applied on top of MetaMorpheus's own default and **validated against
the real schema**: a section/key that doesn't exist raises a clear error rather than being silently
ignored.

```python
import pymetamorpheus as mm

mm.search(
    "run.mzML", "proteins.fasta", "out",
    precursor_tol_ppm=5,                              # named arg
    params={
        "SearchParameters": {"DoParsimony": False, "WritePrunedDatabase": True},
        "CommonParameters.DigestionParams": {"MaxMissedCleavages": 1},
        "CommonParameters": {"TrimMsMsPeaks": False},
    },
)
```

`params` wins over a named argument if both set the same key. Every builder and verb accepts it
(`make_search_task(..., params=...)`, `calibrate(..., params=...)`, and so on).

### Discovering what's available

`available_parameters(task_type)` returns the entire default config as `{section: {key:
default_value}}`, so you can see exactly what `params` accepts:

```python
ap = mm.available_parameters("Search")     # or "Calibration"/"Gptmd"/"GlycoSearch"/"XLSearch"
sum(len(v) for v in ap.values())           # ~112 settings for Search
ap["SearchParameters"]["DoParsimony"]      # "true"
list(ap)                                    # every section header
```

## 3. `run_toml()` — bring your own complete config

For anything the single-line patcher can't express — multi-line arrays, nested tables, a config you
authored in the MetaMorpheus GUI and exported — hand over a complete `.toml` and it runs **verbatim**:

```python
mm.run_toml("MySearchTask.toml", "run.mzML", "proteins.fasta", "out")

# Or compose BYO tasks into a pipeline:
mm.pipeline(
    [mm.task_from_toml("Calib.toml"), mm.task_from_toml("Search.toml")],
    spectra="run.mzML", database="proteins.fasta", output_dir="out",
)
```

A common recipe: generate a default with `available_parameters` as your guide (or the MetaMorpheus
`-g` output), edit it however you like, and run it with `run_toml` — full fidelity, no wrapper in the
way.

## The task types

All five task types MetaMorpheus generates are exposed, each with a verb, a builder, and full `params`
access:

| task | verb | builder |
|---|---|---|
| Search | `search` | `make_search_task` |
| Calibration | `calibrate` | `make_calibration_task` |
| GPTMD | `gptmd` | `make_gptmd_task` |
| Glyco search | `glyco_search` | `make_glyco_search_task` |
| Cross-link (XL) search | `xl_search` | `make_xl_search_task` |

Cross-link and glyco searches have task-specific sections (crosslinker definitions, glycan databases);
reach them through `params` using `available_parameters("XLSearch")` / `available_parameters("GlycoSearch")`
to see the exact keys.
