# Upstream-MetaMorpheus queue

Gaps discovered while building pyMetaMorpheus that belong in **MetaMorpheus**, not here.

The rule this file exists to enforce (decision `D-INHERIT`, from the shared bridge project): a
binding is a **faithful projection**, never a repair site. When something is missing or wrong
upstream, the fix goes upstream and this package carries an honest caveat meanwhile — it does not
quietly paper over the gap in Python. The test for "does this belong upstream?" is whether a native
C# consumer has the identical problem. If a person scripting `CMD.exe` by hand hits it too, it is a
mainland concern.

**Convention:** a caveat is deleted, not maintained, once its fix merges and the pin moves. A caveat
that reads authoritatively and is no longer true is worse than none — it makes people design around
a limit that is not there.

_Last updated: 2026-08-09._

## Open

### U1 — `CMD -g` does not generate `AveragingTask.toml`

| | |
|---|---|
| **What** | `CommandLineSettings.GenerateDefaultTaskTomls` writes five task configs — `CalibrationTask.toml`, `GptmdTask.toml`, `SearchTask.toml`, `XLSearchTask.toml`, `GlycoSearchTask.toml` — and skips spectral averaging, even though `MyTask.Average` is a first-class task type that `Program.cs` will happily run from a supplied TOML into `Task{N}AveragingTask/`. |
| **Native C# consumer affected?** | **Yes.** Anyone scripting `CMD.exe` who runs `-g` to see what a task offers gets five of the six task types. There is no way to obtain MetaMorpheus's own `SpectralAveragingTask` defaults from the command line at all. |
| **How it surfaced** | A code review of pyMetaMorpheus (2026-08-09) flagged that `available_parameters` documented `"Averaging"` as a valid argument while `-g` never produces the file, so the documented call always raised. Checking the claim against the pinned checkout showed the docs were wrong and the generator was incomplete. |
| **Why it matters here** | This package's entire engine is *generate the default TOML with `-g` → patch only the exposed parameters → run*. With no default to patch, averaging cannot become a sibling verb (`mm.average(...)`) the way the other five did. Everything else already lines up: the stem→folder convention yields `Task1AveragingTask/`, dispatch works, and result discovery is generic. |
| **The fix** | Add `SpectralAveragingTask` to `GenerateDefaultTaskTomls` — plus initialising its parameterless constructor, which unlike its five siblings sets neither `Parameters` nor `CommonParameters`, so the naive two-line addition would serialise nulls. |
| **Caveat carried meanwhile** | `available_parameters` documents that `"Averaging"` is unavailable and why; `_engine.py` explains the omission at the point the filename is built. Both are deleted when this lands. |
| **Status** | **OPEN, fix proposed** — issue [MetaMorpheus#2707](https://github.com/smith-chem-wisc/MetaMorpheus/issues/2707), pull request [MetaMorpheus#2708](https://github.com/smith-chem-wisc/MetaMorpheus/pull/2708) (2026-08-09). Verified there by building and running: `-g` writes six tomls, and the generated `AveragingTask.toml` fed straight back in finishes `Task1AveragingTask` and writes an averaged mzML. When it merges: bump the pin, add `average()` / `make_averaging_task()`, and **delete** the caveats in `api.py` and `_engine.py`. |

### U2 — a config file can request a non-specific search and silently get a specific one

| | |
|---|---|
| **What** | `DigestionParams.RecordSpecificProtease()` is what makes a non-specific search work: it copies `Protease` into `SpecificProtease` and then replaces `Protease` with `singleN`/`singleC`. It runs in the **constructor only**. Deserialising a task TOML sets the properties directly, so the file's literal values are used as-is and the rule never fires. |
| **Native C# consumer affected?** | **Yes.** Anyone hand-writing or hand-editing a task TOML — the documented way to drive `CMD.exe` — hits it identically. Nothing about this is Python-specific. |
| **How it surfaced** | A code review of pyMetaMorpheus flagged that its `protease=` argument writes both keys. Checking whether that mattered meant asking what MetaMorpheus does with the pair, and the answer was: whatever the file says. |
| **Verified by running** | A generated `SearchTask.toml` edited to `SearchModeType = "None"` + `Protease = "trypsin"` + `SpecificProtease = "trypsin"`, run through `CMD.exe`, comes back out in MetaMorpheus's own `Task Settings/Task1SearchTaskconfig.toml` as `Protease = "trypsin"` — a full-tryptic search where a non-specific one was requested, with no warning. |
| **Possible fix** | Re-derive the pair after deserialisation (call `RecordSpecificProtease`, or validate the combination and refuse), so a config cannot express a state the constructor would never produce. |
| **Caveat carried meanwhile** | `protease=` refuses to combine with a non-`Full` `SearchModeType` unless the caller sets `Protease` explicitly, and says why. Deleted if this is fixed upstream. |
| **Status** | **OPEN** — not yet filed. |

### What this package does *not* do about it

It does not ship a hand-written `AveragingTask.toml` to patch. That would put MetaMorpheus's own
defaults inside the binding, where they would drift silently at the first pin bump with nothing able
to detect it — the exact repair site `D-INHERIT` forbids. Averaging remains reachable today through
`run_toml()` with a hand-authored config, which is the honest interim answer: the capability is not
blocked, only its convenience wrapper is.

## Resolved

_Nothing yet._
