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
    if isinstance(value, (list, tuple)):
        # MetaMorpheus's configs carry arrays (LocalFdrCategories, CustomIons),
        # available_parameters() reports them, so passing one back has to work.
        return "[" + ", ".join(_format_value(v) for v in value) + "]"
    # UsageError, not TypeError: every other bad-input path in this package raises
    # under PyMetaMorpheusError so a caller can catch the lot, and this one fires
    # late — after the output directory exists and a MetaMorpheus process has
    # already been spawned to generate the defaults.
    raise UsageError(
        f"Cannot write {type(value).__name__} into a TOML value. Supported: "
        "str, bool, int, float, and lists of those."
    )


def parse_value(raw: str) -> object:
    """Parse a TOML scalar/array literal into the Python value it denotes.

    The inverse of :func:`_format_value`, and the reason the two exist as a pair:
    :func:`read_sections` used to hand back the raw right-of-``=`` text, so the
    read-modify-write round trip :func:`pymetamorpheus.available_parameters`
    advertises re-quoted every value it had not touched — ``false`` became the
    string ``"false"``, and ``TaskType = "Search"`` became ``"\\"Search\\""``,
    which MetaMorpheus does not recognise as a task type at all. Values now make
    the trip as Python objects and come back rendered the way they arrived.

    Anything this does not recognise is returned as the raw text unchanged, which
    round-trips through ``_format_value`` as a quoted string — wrong only for
    shapes MetaMorpheus does not currently emit (inline tables, multi-line
    strings). A key nobody can round-trip is better than a key silently corrupted.
    """
    text = raw.strip()
    if not text:
        return ""
    if text == "true":
        return True
    if text == "false":
        return False
    if text.startswith("[") and text.endswith("]"):
        inner = text[1:-1].strip()
        if not inner:
            return []
        # MetaMorpheus's arrays are flat lists of scalars; no nesting to worry about.
        return [parse_value(part) for part in _split_array(inner)]
    if len(text) >= 2 and text[0] == '"' and text[-1] == '"':
        body = text[1:-1]
        out: list[str] = []
        i = 0
        while i < len(body):
            ch = body[i]
            if ch == "\\" and i + 1 < len(body):
                nxt = body[i + 1]
                out.append({"t": "\t", "n": "\n", "r": "\r", '"': '"', "\\": "\\"}.get(nxt, nxt))
                i += 2
                continue
            out.append(ch)
            i += 1
        return "".join(out)
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        pass
    return raw.strip()


def _split_array(inner: str) -> list[str]:
    """Split a flat TOML array body on commas that are not inside a string."""
    parts: list[str] = []
    buf: list[str] = []
    in_string = False
    escaped = False
    for ch in inner:
        if escaped:
            buf.append(ch)
            escaped = False
            continue
        if ch == "\\" and in_string:
            buf.append(ch)
            escaped = True
            continue
        if ch == '"':
            in_string = not in_string
            buf.append(ch)
            continue
        if ch == "," and not in_string:
            parts.append("".join(buf))
            buf = []
            continue
        buf.append(ch)
    if "".join(buf).strip():
        parts.append("".join(buf))
    return parts


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


def read_sections(path: Path) -> dict[str | None, dict[str, object]]:
    """Parse a TOML into ``{section: {key: value}}`` for discovery.

    Read-only and deliberately shallow — it mirrors the same single-line
    ``key = value`` model :func:`patch_toml` edits, so what it reports is exactly
    what ``params`` can override. ``section`` is the exact bracket header, or
    ``None`` for keys before the first section.

    Values are **Python objects** (:func:`parse_value`), not raw TOML text, so the
    dict this returns can be edited and handed straight back as ``params``. It
    used to return raw text, which made that round trip corrupt every key it
    touched — see :func:`parse_value`.
    """
    sections: dict[str | None, dict[str, object]] = {}
    current: str | None = None
    with open(path, "r", encoding="utf-8", newline="") as fh:
        for line in fh:
            stripped = line.strip()
            if stripped.startswith("[") and stripped.endswith("]"):
                current = stripped[1:-1].strip()
                sections.setdefault(current, {})
                continue
            if not stripped or stripped.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            sections.setdefault(current, {})[key.strip()] = parse_value(value)
    return sections


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
