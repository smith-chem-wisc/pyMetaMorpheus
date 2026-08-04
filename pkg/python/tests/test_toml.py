"""Offline unit tests for the dependency-free TOML patcher (no CLI needed)."""

from __future__ import annotations

from pathlib import Path

import pytest

from pymetamorpheus import UsageError
from pymetamorpheus._toml import format_mods, patch_toml

SAMPLE = """\
TaskType = "Search"

[CommonParameters]
MaxThreadsToUsePerFile = 63
ProductMassTolerance = "±20.0000 PPM"
PrecursorMassTolerance = "±5.0000 PPM"
ListOfModsVariable = "Common Variable\\tOxidation on M"

[CommonParameters.DigestionParams]
Protease = "trypsin"
SpecificProtease = "trypsin"
MaxMissedCleavages = 2
"""


def _write(tmp_path: Path, text: str) -> Path:
    p = tmp_path / "SearchTask.toml"
    p.write_text(text, encoding="utf-8")
    return p


def test_patch_common_and_digestion_sections(tmp_path):
    p = _write(tmp_path, SAMPLE)
    applied = patch_toml(
        p,
        {
            ("CommonParameters", "MaxThreadsToUsePerFile"): 8,
            ("CommonParameters", "PrecursorMassTolerance"): "±10.0000 PPM",
            ("CommonParameters.DigestionParams", "Protease"): "chymotrypsin",
            ("CommonParameters.DigestionParams", "MaxMissedCleavages"): 3,
        },
    )
    assert set(applied) == {
        ("CommonParameters", "MaxThreadsToUsePerFile"),
        ("CommonParameters", "PrecursorMassTolerance"),
        ("CommonParameters.DigestionParams", "Protease"),
        ("CommonParameters.DigestionParams", "MaxMissedCleavages"),
    }
    out = p.read_text(encoding="utf-8")
    assert "MaxThreadsToUsePerFile = 8" in out
    assert 'PrecursorMassTolerance = "±10.0000 PPM"' in out
    assert 'Protease = "chymotrypsin"' in out
    assert "MaxMissedCleavages = 3" in out
    # A same-named key in a different section is NOT touched.
    assert 'SpecificProtease = "trypsin"' in out


def test_patch_reports_unmatched_key(tmp_path):
    p = _write(tmp_path, SAMPLE)
    applied = patch_toml(p, {("CommonParameters", "NoSuchKey"): 1})
    assert applied == []  # nothing matched -> caller detects schema drift


def test_patch_preserves_crlf(tmp_path):
    p = tmp_path / "x.toml"
    p.write_bytes(SAMPLE.replace("\n", "\r\n").encode("utf-8"))
    patch_toml(p, {("CommonParameters", "MaxThreadsToUsePerFile"): 4})
    raw = p.read_bytes()
    assert b"MaxThreadsToUsePerFile = 4" in raw.replace(b"\r\n", b"\n")
    assert b"\r\n" in raw
    # No bare LF and no doubled CR: every LF is part of exactly one CRLF.
    assert raw.count(b"\n") == raw.count(b"\r\n")
    assert b"\r\r" not in raw


def test_patch_preserves_lf(tmp_path):
    p = tmp_path / "x.toml"
    p.write_bytes(SAMPLE.encode("utf-8"))  # LF-only
    patch_toml(p, {("CommonParameters", "MaxThreadsToUsePerFile"): 4})
    raw = p.read_bytes()
    assert b"\r" not in raw  # stays LF-only, not flipped to platform CRLF


def test_format_mods_pipe_form():
    s = format_mods(["Common Fixed|Carbamidomethyl on C", "Common Variable|Oxidation on M"])
    assert s == "Common Fixed\tCarbamidomethyl on C\t\tCommon Variable\tOxidation on M"


def test_format_mods_passthrough_and_empty():
    assert format_mods([]) == ""
    already = "Common Variable\tOxidation on M"
    assert format_mods([already]) == already


def test_format_mods_rejects_malformed():
    # Malformed mods raise UsageError (a PyMetaMorpheusError), not a bare
    # ValueError, so every bad-input case is catchable under one hierarchy.
    with pytest.raises(UsageError):
        format_mods(["OxidationOnM"])  # no Category|Name separator
