"""Minimal, dependency-free TOML value patching.

We do NOT parse-and-reserialize TOML (that would need a third-party library and
risk reordering/reformatting MetaMorpheus's carefully-shaped config). Instead we
line-edit: walk the file tracking the current ``[section]``, and replace the
value of specific ``key = ...`` lines in specific sections. Everything else is
left byte-for-byte identical.

This keeps us honest to BRIDGE-PRINCIPLE: MetaMorpheus authored the config via
``CMD -g``; we surgically override only the handful of parameters we expose, and
never invent structure of our own.
"""

from __future__ import annotations

from pathlib import Path

from ._errors import UsageError


def _format_value(value: object) -> str:
    """Render a Python value as its TOML literal (only the shapes we emit)."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return repr(value)
    if isinstance(value, str):
        # Escape backslashes and quotes, then wrap. MetaMorpheus mod strings are
        # tab-delimited; callers pass real "\t" characters which TOML keeps as an
        # escape in a basic string.
        escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\t", "\\t")
        return f'"{escaped}"'
    raise TypeError(f"Unsupported TOML value type: {type(value)!r}")


def patch_toml(
    path: Path,
    overrides: dict[tuple[str | None, str], object],
) -> list[tuple[str | None, str]]:
    """In-place replace values in ``path``.

    ``overrides`` maps ``(section, key) -> new_value`` where ``section`` is the
    exact bracketed header (e.g. ``"CommonParameters"`` or
    ``"CommonParameters.DigestionParams"``) or ``None`` for a key at the top
    level before any section. Returns the list of ``(section, key)`` pairs that
    were actually found and changed, so callers can detect a schema drift (an
    override that matched nothing).
    """
    # Read with newline translation DISABLED (newline="") so the CRLF/LF the
    # file actually uses survives to the detection below — read_text() would
    # normalize CRLF->LF first and defeat it.
    with open(path, "r", encoding="utf-8", newline="") as fh:
        text = fh.read()
    # Preserve the file's existing newline style.
    newline = "\r\n" if "\r\n" in text else "\n"
    lines = text.split(newline)

    current: str | None = None
    applied: list[tuple[str | None, str]] = []

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            current = stripped[1:-1].strip()
            continue
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in line:
            continue
        key = line.split("=", 1)[0].strip()
        target = (current, key)
        if target in overrides:
            indent = line[: len(line) - len(line.lstrip())]
            lines[i] = f"{indent}{key} = {_format_value(overrides[target])}"
            applied.append(target)

    # Write with translation disabled too, so `newline` is the only newline that
    # reaches disk (write_text would re-translate "\n" to os.linesep).
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(newline.join(lines))
    return applied


def format_mods(mods: list[str]) -> str:
    """Turn ``["Common Variable|Oxidation on M", ...]`` into MetaMorpheus's
    tab-delimited ``ListOfMods*`` string.

    MetaMorpheus encodes each mod as ``Category<TAB>Name`` and joins mods with a
    double tab (``<TAB><TAB>``). Callers give us the friendlier ``"Category|Name"``
    form; we translate. Passing an already-tabbed string through unchanged is also
    supported (if it contains a tab we assume it is already formatted).
    """
    if not mods:
        return ""
    parts = []
    for mod in mods:
        if "\t" in mod:  # already in MetaMorpheus form
            parts.append(mod)
            continue
        category, _, name = mod.partition("|")
        if not name:
            # UsageError (not bare ValueError) so callers can catch every
            # bad-input case under PyMetaMorpheusError, like the other validators.
            raise UsageError(
                f"Modification {mod!r} must be 'Category|Name', e.g. "
                "'Common Variable|Oxidation on M'."
            )
        parts.append(f"{category.strip()}\t{name.strip()}")
    return "\t\t".join(parts)
