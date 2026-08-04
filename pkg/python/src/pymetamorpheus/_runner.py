"""The one module that knows how to find and drive the MetaMorpheus CLI.

This is pyMetaMorpheus's ``_runner.py`` — the analogue of pyMzLib's ``_bridge.py``.
Every subprocess concern lives here and nowhere else (decision D5-MM): locating
the executable, generating default TOMLs, invoking a run non-interactively, and
turning a failed process into a typed :class:`RunError`.

Key facts encoded here:

* MetaMorpheus is an *application with an existing CLI* — there is no bespoke
  bridge exe to build. The CLI ``-t <tasks> -s <spectra> -d <databases> -o <out>``
  interface is already the language-neutral wire contract (D6).
* On Windows the executable is ``CMD.exe``; on a framework-dependent Linux/mac
  build it is ``dotnet CMD.dll``. Both are handled by :func:`locate_cli`.
* Runs are fully non-interactive: stdin is closed so a stray prompt surfaces as a
  timeout/failure rather than an infinite hang (see the Thermo ``.raw`` license
  gotcha — sidestepped for now by accepting ``.mzML`` only, gap G-settings).
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from ._errors import MetaMorpheusNotFoundError, RunError

#: Environment variable that pins the MetaMorpheus CLI location (dev + tests).
#: Mirrors mzLibRust's ``MZLIB_BRIDGE`` / pyMzLib's staged-payload override.
ENV_CLI = "PYMM_METAMORPHEUS"

#: Where the wheel stages a self-contained CLI (gitignored; produced at build).
_STAGED_DIRNAME = "_dotnet"


def _staged_cli_dir() -> Path:
    """Directory the build stages the self-contained CLI into, inside the wheel."""
    return Path(__file__).resolve().parent / _STAGED_DIRNAME


# Executable names to probe inside a directory, in preference order. The native
# apphost (CMD.exe on Windows, extensionless CMD on Linux/macOS) is preferred
# because a self-contained build runs WITHOUT a .NET install — the "just works"
# guarantee. CMD.dll is the framework-dependent fallback, launched via `dotnet`.
_EXE_NAMES = ["CMD.exe", "CMD", "CMD.dll"]


def _names_in(directory: Path) -> list[Path]:
    return [directory / name for name in _EXE_NAMES]


def _candidate_paths() -> list[Path]:
    """Ordered CLI locations to probe. First hit wins. Cross-OS: works on
    Windows (CMD.exe), Linux/macOS self-contained (native CMD), and any platform
    with the .NET runtime (CMD.dll via `dotnet`)."""
    candidates: list[Path] = []

    # 1. Explicit override (dev machines, CI, tests). May point at the exe itself
    #    or at the directory containing it.
    env = os.environ.get(ENV_CLI)
    if env:
        p = Path(env)
        if p.is_dir():
            candidates += _names_in(p)
        else:
            candidates.append(p)

    # 2. The self-contained payload staged into the installed wheel (the "just
    #    works" path for end users once G-dist ships).
    candidates += _names_in(_staged_cli_dir())

    return candidates


def locate_cli() -> list[str]:
    """Return the argv prefix that launches MetaMorpheus, e.g. ``["C:/.../CMD.exe"]``
    or ``["dotnet", "C:/.../CMD.dll"]``.

    Raises :class:`MetaMorpheusNotFoundError` with the probed locations if none
    exists, so the failure names the ``PYMM_METAMORPHEUS`` escape hatch.
    """
    probed: list[Path] = []
    for cand in _candidate_paths():
        probed.append(cand)
        if not cand.exists():
            continue
        if cand.suffix.lower() == ".dll":
            return ["dotnet", str(cand)]
        return [str(cand)]

    probed_str = "\n  ".join(str(p) for p in probed)
    raise MetaMorpheusNotFoundError(
        "Could not find the MetaMorpheus CLI. Set the "
        f"{ENV_CLI} environment variable to the CMD executable (or its folder), "
        "or install a pyMetaMorpheus wheel that stages a self-contained CLI.\n"
        f"Looked in:\n  {probed_str}"
    )


def _tail(text: str, n: int = 40) -> str:
    """Last ``n`` non-empty lines of process output, for error messages."""
    lines = [ln for ln in (text or "").splitlines() if ln.strip()]
    return "\n".join(lines[-n:])


def invoke(args: list[str], *, timeout: float | None = None) -> subprocess.CompletedProcess:
    """Run the MetaMorpheus CLI with ``args`` (the flags after the executable).

    Non-interactive by construction: stdin is fed EOF so any interactive prompt
    (e.g. the Thermo ``.raw`` license y/n) errors out instead of hanging forever.
    Raises :class:`RunError` on non-zero exit.
    """
    argv = locate_cli() + list(args)
    try:
        proc = subprocess.run(
            argv,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            # MetaMorpheus emits UTF-8 (e.g. the ± in tolerances, non-ASCII
            # protein names). Decode as UTF-8, not the OS locale codepage
            # (cp1252 on Windows), and never let a stray byte raise inside run().
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as exc:  # dotnet not on PATH, etc.
        raise MetaMorpheusNotFoundError(str(exc)) from exc
    except subprocess.TimeoutExpired as exc:
        raise RunError(
            f"MetaMorpheus timed out after {timeout}s. If the input was a .raw "
            "file this is likely the Thermo license prompt (accept it in "
            "settings.toml, or use .mzML).",
            command=argv,
        ) from exc

    if proc.returncode != 0:
        raise RunError(
            f"MetaMorpheus exited with code {proc.returncode}.\n"
            f"--- stderr (tail) ---\n{_tail(proc.stderr)}\n"
            f"--- stdout (tail) ---\n{_tail(proc.stdout)}",
            returncode=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
            command=argv,
        )
    return proc


def generate_default_tomls(out_dir: Path) -> dict[str, Path]:
    """Run ``CMD -g -o <out_dir>`` and return ``{TaskType.toml basename: path}``.

    This is how we obtain a *complete, current* default config for every task
    type straight from MetaMorpheus itself, rather than hand-maintaining TOML
    templates that would drift from the engine (BRIDGE-PRINCIPLE: the mainland
    owns the schema; we project it).
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    invoke(["-g", "-o", str(out_dir)], timeout=120)
    tomls = {p.name: p for p in out_dir.glob("*.toml")}
    if not tomls:
        raise RunError(
            f"'CMD -g' produced no .toml files in {out_dir}.", command=["-g"]
        )
    return tomls
