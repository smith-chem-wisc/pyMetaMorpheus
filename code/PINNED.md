# Pinned MetaMorpheus build

pyMetaMorpheus is a projection of a *specific* MetaMorpheus build. This file records the pin the
staged CLI payload (`pkg/build/publish-runner.ps1` → `src/pymetamorpheus/_dotnet/`) is built from.
The checkout itself is gitignored (`code/MetaMorpheus/`) — this record is the reproducible pointer.

| field | value |
|---|---|
| repo | https://github.com/smith-chem-wisc/MetaMorpheus |
| commit | `3b9f634ec9cf7a1a2d04ca2e9c761bdd6e26eae3` |
| branch | `master` |
| describe | `1.1.7-25-g3b9f634ec` |
| date | 2026-07-28 |
| subject | MetaDraw Update: m/z restrictions, diagnostic refragmentation, and Glyco Refragmentation (#2694) |
| local checkout | `E:\GitClones\MetaMorpheus` |

## Grounding facts captured from this build

- CLI executable (dev): `MetaMorpheus\CMD\bin\Debug\net8.0\CMD.exe`
- `CMD -g` generates: `CalibrationTask.toml`, `GptmdTask.toml`, `SearchTask.toml`,
  `GlycoSearchTask.toml`, `AveragingTask.toml`, `XLSearchTask.toml`.
- Task TaskType values: `Calibrate` / `Gptmd` / `Search` / `GlycoSearch` (the TOML *filenames* use the
  `CalibrationTask` / `GptmdTask` / `SearchTask` / `GlycoSearchTask` stems).
- Output folders: `Task<N><TaskType>Task/` (e.g. `Task1SearchTask/`, `Task2GptmdTask/`).
- Glyco params live in the `[_glycoSearchParameters]` section (`GlycoSearchType`, glycan DBs).
- Common params + `[CommonParameters.DigestionParams]` (`Protease` and `SpecificProtease` both set).
- Verified end-to-end via the Python API: classic search on bundled
  `SmallCalibratible_Yeast.mzML` + `SmallYeast.fasta` → `Task1SearchTask/AllPSMs.psmtsv` (89 PSMs).

## Bumping the pin

1. `git -C E:\GitClones\MetaMorpheus pull` (or check out the desired tag/commit).
2. Rebuild the staged payload for each RID: `pwsh pkg/build/publish-runner.ps1 -Rid <rid> -MetaMorpheusRoot E:\GitClones\MetaMorpheus`.
3. Re-run the offline + live test suites.
4. Update the table above and add a CHANGELOG entry.
