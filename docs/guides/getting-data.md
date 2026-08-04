# Getting your data

A run needs two inputs: **spectra** (`.mzML`) and a **protein database** (`.fasta` or UniProt `.xml`,
optionally `.gz`). Its sibling binding, [pyMzLib](https://github.com/smith-chem-wisc/pyMzLib), can
fetch both from public repositories, so you can go from an accession to a finished search entirely in
Python.

!!! note "Installing pyMzLib"
    pyMzLib isn't on PyPI yet — install it with `pip install "pymetamorpheus[pymzlib]"` (which pulls
    it from source over git), or clone it directly. Don't `pip install pymzlib` on its own; an
    unrelated package of that name exists on PyPI.

## Spectra and files from PRIDE

The [PRIDE Archive](https://www.ebi.ac.uk/pride/) hosts published proteomics datasets. pyMzLib lists a
project's files and downloads exactly the ones you choose.

```python
import pymzlib

# What's in a project?
files = pymzlib.pride.list_files("PXD000001")
for f in files:
    print(f.file_name, f"{f.size_mb:.1f} MB", f.extension(), "downloadable" if f.downloadable else "")
```

Each entry is a `PrideFile` with `file_name`, `file_size_bytes` / `size_mb`, `https_url`,
`extension()`, and `downloadable`. Filter the manifest with plain Python, then download just those:

```python
# Grab the mzML spectra and any FASTA the project ships, skipping huge/raw files.
wanted = [
    f for f in files
    if f.downloadable and f.extension() in {".mzml", ".fasta"} and f.size_mb < 500
]
paths = pymzlib.pride.download_files(wanted, "data")   # -> list[Path]
print("downloaded:", [p.name for p in paths])
```

There's also a one-shot `download(accession, destination, extensions=[".mzml"])` if you don't need to
inspect the manifest first.

!!! warning "PRIDE is mostly `.raw`"
    Many projects publish only vendor `.raw` files (and some list files only over Aspera, which show
    as `downloadable = False`). pyMetaMorpheus needs `.mzML`, so prefer projects that publish `.mzML`,
    or convert `.raw` with MSConvert.

## Protein databases from UniProt

For a **search database** (a whole proteome), download it straight from UniProt's REST API. The
standard library is enough, and pyMetaMorpheus reads the `.gz` directly:

```python
import urllib.request

# Reviewed (Swiss-Prot) human proteome, gzipped FASTA.
url = ("https://rest.uniprot.org/uniprotkb/stream"
       "?query=organism_id:9606+AND+reviewed:true&format=fasta&compressed=true")
urllib.request.urlretrieve(url, "human_sp.fasta.gz")
```

Change `organism_id` for another species (e.g. `559292` for *S. cerevisiae*), or drop
`reviewed:true` to include TrEMBL. UniProt `.xml` (`format=xml`) works too and carries annotated
modifications GPTMD can use.

!!! note "pyMzLib and UniProt"
    pyMzLib's UniProt support is `pymzlib.peptidoform.fragments("P02768", ...)` — it fetches a
    **single entry**, digests it, and fragments the peptides for peptidoform analysis. It does **not**
    download whole proteomes, so use the UniProt REST endpoint above for a search database.

## Putting it together

```python
import pymzlib, pymetamorpheus as mm, urllib.request

# 1. spectra from PRIDE (pick a project that publishes a small mzML)
files = pymzlib.pride.list_files("PXD_EXAMPLE")
mzml = min((f for f in files if f.extension() == ".mzml" and f.downloadable), key=lambda f: f.size_mb)
[spectra] = pymzlib.pride.download_files([mzml], "data")

# 2. database from UniProt
urllib.request.urlretrieve(
    "https://rest.uniprot.org/uniprotkb/stream?query=organism_id:9606+AND+reviewed:true"
    "&format=fasta&compressed=true", "data/human_sp.fasta.gz")

# 3. search
result = mm.search(spectra, "data/human_sp.fasta.gz", "out",
                   precursor_tol_ppm=10, product_tol_ppm=20)
print(result.search.summary.read_text(encoding="utf-8"))
```

This is exactly the path an independent reviewer used to validate pyMetaMorpheus on a real 227 MB human
PRIDE dataset — self-fetched with pyMzLib, searched against UniProt human Swiss-Prot.
