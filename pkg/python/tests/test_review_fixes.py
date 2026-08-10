"""Regression tests for the four defects the 2026-08-09 code review confirmed.

Each of these fails against the code as it stood before the fix. That matters more
than the passing: a guard written only against a healthy tree cannot tell you
whether it detects anything.

Three of the four produced *silently wrong results* rather than an error, which is
why they are pinned here rather than left to the live suite — none of them raised,
so nothing short of asserting the value would have caught them.
"""

from __future__ import annotations

import pytest

import pymetamorpheus as mm
from pymetamorpheus._engine import Task, common_overrides, select_run_tasks
from pymetamorpheus._toml import parse_value, patch_toml, read_sections
from pymetamorpheus.results import discover_tasks


# --- Finding 1: available_parameters -> params round trip -----------------------


def test_read_sections_returns_python_values(tmp_path):
    p = tmp_path / "t.toml"
    p.write_text(
        'TaskType = "Search"\n'
        "\n[SearchParameters]\n"
        "DoParsimony = true\n"
        "DoHistogramAnalysis = false\n"
        "QuantifyPpmTol = 5.0\n"
        "MaxThreads = 63\n"
        'DecoyType = "Reverse"\n'
        'LocalFdrCategories = ["FullySpecific"]\n'
        "CustomIons = []\n",
        encoding="utf-8",
    )
    s = read_sections(p)
    assert s[None]["TaskType"] == "Search"
    sp = s["SearchParameters"]
    assert sp["DoParsimony"] is True
    assert sp["DoHistogramAnalysis"] is False
    assert sp["QuantifyPpmTol"] == 5.0
    assert sp["MaxThreads"] == 63
    assert sp["DecoyType"] == "Reverse"
    assert sp["LocalFdrCategories"] == ["FullySpecific"]
    assert sp["CustomIons"] == []


def test_round_trip_leaves_the_file_unchanged(tmp_path):
    """Read every key, write every key back untouched, expect a byte-identical file.

    This is the whole defect in one assertion. Before the fix the rewrite quoted
    everything: `DoParsimony = "true"`, and `TaskType = "\\"Search\\""` — which
    MetaMorpheus does not recognise, so it skipped the task, exited 0, and the
    resulting error blamed the engine.
    """
    original = (
        'TaskType = "Search"\n'
        "\n[SearchParameters]\n"
        "DoParsimony = true\n"
        "QuantifyPpmTol = 5.0\n"
        'DecoyType = "Reverse"\n'
        'LocalFdrCategories = ["FullySpecific"]\n'
    )
    p = tmp_path / "t.toml"
    p.write_text(original, encoding="utf-8")

    sections = read_sections(p)
    overrides = {
        (section, key): value
        for section, keys in sections.items()
        for key, value in keys.items()
    }
    patch_toml(p, overrides)

    assert p.read_text(encoding="utf-8") == original


def test_tab_delimited_mod_strings_survive_the_round_trip(tmp_path):
    """MetaMorpheus's ListOfMods* values carry escaped tabs; they must not double up."""
    original = 'ListOfModsFixed = "Common Fixed\\tCarbamidomethyl on C"\n'
    p = tmp_path / "t.toml"
    p.write_text(original, encoding="utf-8")

    value = read_sections(p)[None]["ListOfModsFixed"]
    assert value == "Common Fixed\tCarbamidomethyl on C"  # real tab, unescaped

    patch_toml(p, {(None, "ListOfModsFixed"): value})
    assert p.read_text(encoding="utf-8") == original


def test_unsupported_value_raises_usage_error_not_typeerror():
    """Every bad-input path in this package must be catchable as PyMetaMorpheusError."""
    with pytest.raises(mm.UsageError):
        patch_toml.__globals__["_format_value"]({"a": 1})


def test_parse_value_leaves_unrecognised_text_alone():
    assert parse_value("{ inline = 1 }") == "{ inline = 1 }"


# --- Finding 2: stale task folders from an earlier run --------------------------


def test_discovery_ignores_folders_above_this_runs_task_count(tmp_path):
    """A 3-task pipeline then a 1-task search into the same output directory.

    Before the fix, discovery returned all four folders and `RunResult.search`
    took the LAST match — the pipeline's stale search rather than the one just
    run — while the "produced nothing" guard was satisfied by the leftovers.
    """
    for name in (
        "Task1CalibrationTask",
        "Task2GptmdTask",
        "Task3SearchTask",  # stale: from the earlier pipeline
    ):
        (tmp_path / name).mkdir()
    (tmp_path / "Task1SearchTask").mkdir()  # this run

    found = discover_tasks(tmp_path)
    assert len(found) == 4, "discovery still reports what is on disk"

    # Index alone cannot separate them: the stale Task1CalibrationTask shares
    # index 1 with this run's Task1SearchTask.
    selected = select_run_tasks(
        found,
        [Task(task_type="Search")],
        pre_existing={"Task1CalibrationTask", "Task2GptmdTask", "Task3SearchTask"},
    )
    assert [t.directory.name for t in selected] == ["Task1SearchTask"]


def test_rerunning_the_same_task_into_the_same_directory_still_reports_it(tmp_path):
    """The folder existed before the run and was overwritten by it — still ours."""
    (tmp_path / "Task1SearchTask").mkdir()
    selected = select_run_tasks(
        discover_tasks(tmp_path),
        [Task(task_type="Search")],
        pre_existing={"Task1SearchTask"},
    )
    assert [t.directory.name for t in selected] == ["Task1SearchTask"]


def test_byo_toml_task_folder_is_claimed_by_index(tmp_path):
    """A bring-your-own TOML has no predictable folder name, so it is claimed by
    being new — and, if it overwrote its own folder from a previous run, by index."""
    (tmp_path / "Task1SearchTask").mkdir()
    byo = Task(toml_path=tmp_path / "mine.toml")
    selected = select_run_tasks(discover_tasks(tmp_path), [byo], pre_existing=set())
    assert [t.directory.name for t in selected] == ["Task1SearchTask"]

    selected = select_run_tasks(
        discover_tasks(tmp_path), [byo], pre_existing={"Task1SearchTask"}
    )
    assert [t.directory.name for t in selected] == ["Task1SearchTask"]


# --- Finding 3: protease= silently un-does a non-specific search ----------------


def test_protease_with_nonspecific_search_mode_is_refused():
    """mzLib keeps Protease and SpecificProtease deliberately different for a
    non-specific search (singleN/singleC vs the real enzyme), and does not derive
    that when reading a config. Writing the enzyme into both keys would run a
    full-tryptic search instead — verified against MetaMorpheus by running it.
    """
    with pytest.raises(mm.UsageError) as excinfo:
        common_overrides(
            protease="trypsin",
            params={"CommonParameters.DigestionParams": {"SearchModeType": "None"}},
        )
    assert "singleN" in str(excinfo.value)


def test_protease_is_allowed_when_the_caller_sets_protease_itself():
    ov = common_overrides(
        protease="trypsin",
        params={
            "CommonParameters.DigestionParams": {
                "SearchModeType": "None",
                "Protease": "singleC",
                "SpecificProtease": "trypsin",
            }
        },
    )
    # No refusal: the caller has taken responsibility for both keys.
    assert ov[("CommonParameters.DigestionParams", "SpecificProtease")] == "trypsin"


def test_protease_still_writes_both_keys_for_a_normal_search():
    ov = common_overrides(protease="chymotrypsin")
    dp = "CommonParameters.DigestionParams"
    assert ov[(dp, "Protease")] == "chymotrypsin"
    assert ov[(dp, "SpecificProtease")] == "chymotrypsin"


def test_protease_is_allowed_with_an_explicitly_full_search_mode():
    ov = common_overrides(
        protease="trypsin",
        params={"CommonParameters.DigestionParams": {"SearchModeType": "Full"}},
    )
    assert ov[("CommonParameters.DigestionParams", "Protease")] == "trypsin"


# --- Finding 4: all_proteins misses the unquantified filename -------------------


def _task(tmp_path, name, files):
    d = tmp_path / name
    d.mkdir()
    for f in files:
        (d / f).write_text("x", encoding="utf-8")
    return discover_tasks(tmp_path)[0]


def test_all_proteins_finds_the_unquantified_file(tmp_path):
    """`search(..., quantify=False)` produces AllProteinGroups.tsv, not the
    AllQuantified... name. Returning None for it reads as "no proteins found"."""
    t = _task(tmp_path, "Task1SearchTask", ["AllProteinGroups.tsv"])
    assert t.all_proteins is not None
    assert t.all_proteins.name == "AllProteinGroups.tsv"


def test_all_proteins_prefers_the_quantified_file(tmp_path):
    t = _task(
        tmp_path,
        "Task1SearchTask",
        ["AllProteinGroups.tsv", "AllQuantifiedProteinGroups.tsv"],
    )
    assert t.all_proteins.name == "AllQuantifiedProteinGroups.tsv"


def test_quantified_proteins_does_not_fall_back(tmp_path):
    """Asking for quantified proteins when quantification did not run has no
    answer, and None is the honest one — the fallback would hand back a file that
    carries no intensities."""
    t = _task(tmp_path, "Task1SearchTask", ["AllProteinGroups.tsv"])
    assert t.quantified_proteins is None
