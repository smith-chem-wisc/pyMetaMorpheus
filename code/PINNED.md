# The MetaMorpheus build this package projects

pyMetaMorpheus is a faithful projection of a *specific* MetaMorpheus build. This file is the
provenance record for that build: which release it relates to, what was verified against it, and how
to move it.

**The commit itself is not written here.** It lives in [`code/metamorpheus.pin`](metamorpheus.pin),
a plain file holding one 40-character sha, and that is the only copy. Every consumer reads it:

| consumer | how it reads the pin |
|---|---|
| `pkg/build/publish-runner.ps1` | reads it, then refuses to stage a checkout whose `HEAD` is a different commit (override with `-IgnorePin`) |
| `.github/workflows/ci.yml` (live canary) | fetches exactly that commit from MetaMorpheus and asserts `HEAD` matches |
| `.github/workflows/upstream-watch.yml` | compares it against MetaMorpheus's latest release and opens a bump pull request when the release is genuinely ahead |

Anything that needs the value should read the file. Restating it in prose is how the record and the
build come to disagree, and the copy nobody builds from is always the one that goes stale.

## The pin can sit ahead of the latest release

Nothing requires the pin to be a release commit, and as of **2026-08-09** it was not: it sat 25
commits past `1.1.7`, taken from `master`. That is why `upstream-watch.yml` compares *direction*
rather than mere difference. A watcher that only asked "is the latest release a different commit?"
would have opened a pull request every Monday proposing to roll the build **backwards** onto 1.1.7.

Everything in this section is a dated observation rather than a standing claim, deliberately: the
watcher appends to the history table at the bottom and never edits prose, so any sentence here
written in the present tense would quietly become false at the first bump. To ask what the pin is
today, read `code/metamorpheus.pin`; to ask how it relates to upstream today, run the watcher.

## Grounding facts captured from the build

Read off the initial pin of 2026-07-28 (*"MetaDraw Update: m/z restrictions, diagnostic
refragmentation, and Glyco Refragmentation (#2694)"*) by running it, not from documentation. They are
what the TOML writer and the result-path logic encode:

- CLI executable (dev): `MetaMorpheus\CMD\bin\Debug\net8.0\CMD.exe`
- `CMD -g` generates: `CalibrationTask.toml`, `GptmdTask.toml`, `SearchTask.toml`,
  `GlycoSearchTask.toml`, `AveragingTask.toml`, `XLSearchTask.toml`.
- Task TaskType values: `Calibrate` / `Gptmd` / `Search` / `GlycoSearch` (the TOML *filenames* use the
  `CalibrationTask` / `GptmdTask` / `SearchTask` / `GlycoSearchTask` stems).
- Output folders: `Task<N><TaskType>Task/` (e.g. `Task1SearchTask/`, `Task2GptmdTask/`).
- Glyco params live in the `[_glycoSearchParameters]` section (`GlycoSearchType`, glycan DBs).
- Common params + `[CommonParameters.DigestionParams]` (`Protease` and `SpecificProtease` both set).
- Verified end-to-end through the Python API: classic search on bundled
  `SmallCalibratible_Yeast.mzML` + `SmallYeast.fasta` → `Task1SearchTask/AllPSMs.psmtsv` (89 PSMs).

A grounding fact is not a duplicated value — nothing else in the repository holds these, and they are
exactly what would silently change under a careless bump. If one of them stops being true, the bump
that broke it is a behaviour change, not a routine re-pin.

## Bumping the pin

`upstream-watch.yml` proposes bumps automatically when MetaMorpheus cuts a release that is ahead of
the pin. It opens a pull request rather than pushing, because CI's live canary — which builds a
self-contained CLI from the pinned commit and runs a real search through the Python API — is the
evidence that the new build is safe, and that evidence only exists if the pull request runs it.

To bump by hand:

1. `printf '%s\n' <sha> > code/metamorpheus.pin`
2. Rebuild the staged payload for each RID:
   `pwsh pkg/build/publish-runner.ps1 -Rid <rid> -MetaMorpheusRoot <checkout>`
3. Re-run the offline and live suites.
4. Re-check the grounding facts above if the range touches the CMD, task or TOML surface.
5. Append a row to the history table below and add a changelog entry.

What CI cannot judge is whether a commit in the range **changes a value MetaMorpheus reports**. A
pure projection is routine; a changed number is a judgement call. Skim the range with that in mind.

## Pin history

<!-- This table MUST remain the last thing in this file: upstream-watch.yml appends one row to the
     end of the file when it bumps the pin. Anything written below it would end up inside the table. -->

| date | commit | release | note |
|---|---|---|---|
| 2026-07-28 | `3b9f634e` | 25 commits after `1.1.7` | initial pin; the build every grounding fact above was read from |
