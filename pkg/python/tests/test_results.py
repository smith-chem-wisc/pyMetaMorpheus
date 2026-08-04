"""Offline tests for run-directory discovery against a fabricated run tree."""

from __future__ import annotations

from pymetamorpheus.results import RunResult, discover_tasks


def _fake_run(tmp_path):
    """A run dir shaped like a calibrate -> GPTMD -> search pipeline."""
    (tmp_path / "Task1CalibrationTask").mkdir()
    (tmp_path / "Task1CalibrationTask" / "run-calib.mzML").write_text("x")
    (tmp_path / "Task2GptmdTask").mkdir()
    (tmp_path / "Task2GptmdTask" / "proteinsGPTMD.xml").write_text("x")
    (tmp_path / "Task3SearchTask").mkdir()
    (tmp_path / "Task3SearchTask" / "AllPSMs.psmtsv").write_text("h\nr1\n")
    (tmp_path / "Task3SearchTask" / "results.mzID").write_text("x")
    # A stray non-task folder must be ignored.
    (tmp_path / "Task_scratch_junk").mkdir()
    (tmp_path / "notes.txt").write_text("x")
    return tmp_path


def test_discover_orders_by_index(tmp_path):
    tasks = discover_tasks(_fake_run(tmp_path))
    assert [(t.index, t.task_type) for t in tasks] == [
        (1, "CalibrationTask"),
        (2, "GptmdTask"),
        (3, "SearchTask"),
    ]


def test_runresult_accessors(tmp_path):
    r = RunResult(output_dir=_fake_run(tmp_path))
    r.tasks = discover_tasks(r.output_dir)
    assert r.search is not None
    assert r.search.all_psms is not None and r.search.all_psms.name == "AllPSMs.psmtsv"
    assert r.search.mzid and r.search.mzid[0].suffix == ".mzID"
    assert r.calibration.calibrated_spectra[0].name == "run-calib.mzML"
    assert r.gptmd.gptmd_database[0].name == "proteinsGPTMD.xml"
    assert r.glyco_search is None  # no glyco task in this run


def test_missing_file_returns_none(tmp_path):
    (tmp_path / "Task1SearchTask").mkdir()
    tasks = discover_tasks(tmp_path)
    assert tasks[0].all_proteins is None  # not written in this fake run
