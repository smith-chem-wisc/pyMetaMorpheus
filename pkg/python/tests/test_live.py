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
