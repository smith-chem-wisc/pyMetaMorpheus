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
| **The fix** | Add `SpectralAveragingTask` to `GenerateDefaultTaskTomls`, mirroring the other five (two lines). |
| **Caveat carried meanwhile** | `available_parameters` documents that `"Averaging"` is unavailable and why; `_engine.py` explains the omission at the point the filename is built. Both are deleted when this lands. |
| **Status** | **OPEN** — [MetaMorpheus#2707](https://github.com/smith-chem-wisc/MetaMorpheus/issues/2707), filed 2026-08-09. |

### What this package does *not* do about it

It does not ship a hand-written `AveragingTask.toml` to patch. That would put MetaMorpheus's own
defaults inside the binding, where they would drift silently at the first pin bump with nothing able
to detect it — the exact repair site `D-INHERIT` forbids. Averaging remains reachable today through
`run_toml()` with a hand-authored config, which is the honest interim answer: the capability is not
blocked, only its convenience wrapper is.

## Resolved

_Nothing yet._
