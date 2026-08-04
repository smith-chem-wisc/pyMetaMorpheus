# Installation & locating the CLI

## Installing

```bash
pip install pymetamorpheus
```

pyMetaMorpheus has **zero required third-party dependencies**. Optional extras:

| extra | pulls in | for |
|---|---|---|
| `pymetamorpheus[pymzlib]` | pyMzLib | parsing result files into typed tables |
| `pymetamorpheus[pandas]` | pandas | DataFrame convenience |
| `pymetamorpheus[dev]` | pytest, pytest-cov | running the test suite |

## How the MetaMorpheus CLI is found

pyMetaMorpheus drives the MetaMorpheus command-line program. The runner locates it in this order:

1. **`PYMM_METAMORPHEUS`** environment variable — the path to `CMD.exe` (Windows) / `CMD.dll`
   (framework-dependent build), or the folder that contains it. This is what you use on a dev machine
   or in CI against a local MetaMorpheus checkout:

    ```bash
    # Windows
    set PYMM_METAMORPHEUS=E:\GitClones\MetaMorpheus\MetaMorpheus\CMD\bin\Release\net8.0\CMD.exe
    # POSIX
    export PYMM_METAMORPHEUS=/path/to/CMD.dll
    ```

2. **A self-contained payload staged inside the installed wheel** — the "just works" path for end
   users. (Distribution of this payload is being finalized; see the note below.)

If neither is found, calling a verb raises `MetaMorpheusNotFoundError` listing the locations probed
and naming the `PYMM_METAMORPHEUS` escape hatch.

!!! info "Distribution of the bundled CLI"
    A self-contained MetaMorpheus build is large, and can exceed PyPI's 100 MB per-file limit. The
    shipping model — bundle in the wheel vs. download-at-install on first use — is being decided
    before the first public release (project gap **G-dist**). Until then, use `PYMM_METAMORPHEUS`
    against a MetaMorpheus build you already have.

## Cross-platform

pyMetaMorpheus runs on **Windows, Linux, and macOS** (including Apple Silicon), just like pyMzLib.
There is nothing OS-specific in the Python code — it drives whichever MetaMorpheus executable it
finds:

| platform | executable it launches |
|---|---|
| Windows | `CMD.exe` (native apphost) |
| Linux / macOS, self-contained build | `CMD` (native apphost — **no .NET install needed**) |
| any platform with the .NET runtime | `CMD.dll` via `dotnet` |

The runner prefers the native self-contained apphost so that an installed wheel works on a machine
with **no .NET runtime present** — the same "just works" guarantee pyMzLib makes. Per-platform wheels
are built by `pkg/build/publish-runner.ps1 -Rid win-x64|linux-x64|osx-x64|osx-arm64` (pwsh and
`dotnet publish` are themselves cross-platform, so every wheel is producible from CI).

## Verifying your install

```python
import pymetamorpheus as mm
print(mm.__version__)
```

Then run the bundled small test against a MetaMorpheus checkout to confirm the round-trip:

```python
import os, pymetamorpheus as mm
os.environ["PYMM_METAMORPHEUS"] = r"...\CMD\bin\Release\net8.0\CMD.exe"
data = r"...\MetaMorpheus\EngineLayer\Data"
result = mm.search(
    os.path.join(data, "SmallCalibratible_Yeast.mzML"),
    os.path.join(data, "SmallYeast.fasta"),
    "out",
)
print(result.search.all_psms)   # AllPSMs.psmtsv should exist
```
