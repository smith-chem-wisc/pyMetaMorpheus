"""Offline tests for the arbitrary-parameter passthrough, BYO-TOML, and the
read-only section parser (no CLI needed)."""

from __future__ import annotations

from pathlib import Path

import pytest

import pymetamorpheus as mm
from pymetamorpheus._engine import normalize_params
from pymetamorpheus._toml import read_sections


def test_normalize_params_nested():
    ov = normalize_params(
        {
            "CommonParameters": {"MaxThreadsToUsePerFile": 8},
            "CommonParameters.DigestionParams": {"MaxMissedCleavages": 3},
            "": {"TaskType": "Search"},  # pre-section key
        }
    )
    assert ov[("CommonParameters", "MaxThreadsToUsePerFile")] == 8
    assert ov[("CommonParameters.DigestionParams", "MaxMissedCleavages")] == 3
    assert ov[(None, "TaskType")] == "Search"


def test_normalize_params_empty_and_bad():
    assert normalize_params(None) == {}
    assert normalize_params({}) == {}
    with pytest.raises(mm.UsageError):
        normalize_params({"SearchParameters": "notadict"})


def test_params_merge_into_builder_and_win():
    # params override the curated named arg for the same key (passthrough wins).
    t = mm.make_search_task(
        max_threads=4, params={"CommonParameters": {"MaxThreadsToUsePerFile": 16}}
    )
    assert t.overrides[("CommonParameters", "MaxThreadsToUsePerFile")] == 16
    # and can set a key that has no named argument at all:
    t2 = mm.make_search_task(params={"SearchParameters": {"DoParsimony": False}})
    assert t2.overrides[("SearchParameters", "DoParsimony")] is False


def test_params_reaches_arbitrary_section():
    t = mm.make_gptmd_task(params={"GptmdParameters": {"SomeKnob": 5}})
    assert t.overrides[("GptmdParameters", "SomeKnob")] == 5


def test_task_from_toml_shape(tmp_path):
    p = tmp_path / "MyTask.toml"
    p.write_text('TaskType = "Search"\n', encoding="utf-8")
    t = mm.task_from_toml(p)
    assert t.toml_path == p
    assert t.task_type is None  # BYO tasks have no engine-assigned type


def test_read_sections(tmp_path):
    p = tmp_path / "x.toml"
    p.write_text(
        'TaskType = "Search"\n\n[CommonParameters]\nMaxThreadsToUsePerFile = 63\n'
        '\n[CommonParameters.DigestionParams]\nProtease = "trypsin"\n',
        encoding="utf-8",
    )
    s = read_sections(p)
    assert s[None]["TaskType"] == '"Search"'
    assert s["CommonParameters"]["MaxThreadsToUsePerFile"] == "63"
    assert s["CommonParameters.DigestionParams"]["Protease"] == '"trypsin"'
