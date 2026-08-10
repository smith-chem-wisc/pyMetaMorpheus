"""Live canary tests — invoke the real MetaMorpheus CLI.

Marked ``live`` and self-skipping unless ``PYMM_METAMORPHEUS`` points at a
runnable CLI, so the offline suite stays green on any machine. Run explicitly::

    pytest -m live
"""

from __future__ import annotations

import pytest

import pymetamorpheus as mm

pytestmark = pytest.mark.live


def test_classic_search_produces_psms(cli_or_skip, sample_data, tmp_path):
    result = mm.search(
        sample_data["spectra"],
        sample_data["database"],
        tmp_path / "out",
        precursor_tol_ppm=5,
        product_tol_ppm=20,
        variable_mods=["Common Variable|Oxidation on M"],
        max_threads=8,
        timeout=1800,
    )
    assert result.search is not None
    psms = result.search.all_psms
    assert psms is not None and psms.exists()
    # Header + at least one PSM row on this well-behaved sample.
    rows = psms.read_text(encoding="utf-8").splitlines()
    assert len(rows) >= 2


def test_calibration_produces_calibrated_spectra(cli_or_skip, sample_data, tmp_path):
    result = mm.calibrate(
        sample_data["spectra"], sample_data["database"], tmp_path / "out", timeout=1800
    )
    assert result.calibration is not None
    assert result.calibration.calibrated_spectra, "expected a *-calib.mzML"


def test_available_parameters_all_task_types(cli_or_skip):
    # Every exposed task type generates and parses into non-empty sections.
    for tt in ["Search", "Calibration", "Gptmd", "GlycoSearch", "XLSearch"]:
        sections = mm.available_parameters(tt)
        total = sum(len(v) for v in sections.values())
        assert total > 0, f"{tt} exposed no parameters"


def test_params_passthrough_lands_in_run(cli_or_skip, sample_data, tmp_path):
    # A param with no named argument must reach the actually-run config.
    from pymetamorpheus._toml import read_sections

    out = tmp_path / "out"
    mm.search(
        sample_data["spectra"], sample_data["database"], out,
        params={"SearchParameters": {"DoParsimony": False}},
        timeout=1800,
    )
    cfg = next(out.glob("**/Task Settings/*config.toml"))
    assert read_sections(cfg)["SearchParameters"]["DoParsimony"] is False


def test_run_toml_verbatim(cli_or_skip, sample_data, tmp_path):
    from pymetamorpheus._runner import generate_default_tomls

    gen = tmp_path / "gen"
    defaults = generate_default_tomls(gen)
    r = mm.run_toml(defaults["SearchTask.toml"], sample_data["spectra"],
                    sample_data["database"], tmp_path / "out", timeout=1800)
    assert r.task("SearchTask") is not None
    assert r.task("SearchTask").all_psms is not None
