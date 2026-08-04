"""Offline tests for input validation and override building (no CLI needed)."""

from __future__ import annotations

import pytest

import pymetamorpheus as mm
from pymetamorpheus._engine import (
    _validate_databases,
    _validate_spectra,
    common_overrides,
)


def _touch(dir_, name):
    p = dir_ / name
    p.write_text("stub", encoding="utf-8")
    return p


def test_raw_rejected_before_process(tmp_path):
    # .raw is rejected on the extension, regardless of existence (mzML-only, G-settings).
    raw = _touch(tmp_path, "run.raw")
    with pytest.raises(mm.UsageError) as exc:
        _validate_spectra(raw)
    assert ".raw" in str(exc.value) or "raw support is deferred" in str(exc.value)


def test_unsupported_extension_reported_even_if_missing():
    with pytest.raises(mm.UsageError) as exc:
        _validate_spectra("nope.wiff")
    assert "Unsupported spectra format" in str(exc.value)


def test_mzml_missing_is_not_found(tmp_path):
    with pytest.raises(mm.UsageError) as exc:
        _validate_spectra(str(tmp_path / "absent.mzML"))
    assert "not found" in str(exc.value)


def test_mzml_accepted(tmp_path):
    p = _touch(tmp_path, "run.mzML")
    assert _validate_spectra(p) == [p]


def test_database_extensions(tmp_path):
    fasta = _touch(tmp_path, "proteins.fasta")
    assert _validate_databases(fasta) == [fasta]
    with pytest.raises(mm.UsageError):
        _validate_databases(_touch(tmp_path, "proteins.txt"))


def test_common_overrides_only_sets_provided():
    ov = common_overrides(precursor_tol_ppm=5, max_threads=8)
    assert ov[("CommonParameters", "PrecursorMassTolerance")] == "±5.0000 PPM"
    assert ov[("CommonParameters", "MaxThreadsToUsePerFile")] == 8
    # Unspecified knobs produce no override (keep MetaMorpheus defaults).
    assert ("CommonParameters", "ProductMassTolerance") not in ov
    assert ("CommonParameters.DigestionParams", "Protease") not in ov


def test_common_overrides_protease_sets_both_keys():
    ov = common_overrides(protease="chymotrypsin")
    dp = "CommonParameters.DigestionParams"
    assert ov[(dp, "Protease")] == "chymotrypsin"
    assert ov[(dp, "SpecificProtease")] == "chymotrypsin"


def test_common_overrides_rejects_bad_threads():
    with pytest.raises(mm.UsageError):
        common_overrides(max_threads=0)


def test_task_builders_shape():
    assert mm.make_search_task().task_type == "Search"
    assert mm.make_calibration_task().toml_filename == "CalibrationTask.toml"
    assert mm.make_gptmd_task().toml_filename == "GptmdTask.toml"
    g = mm.make_glyco_search_task(glyco_search_type="NGlycanSearch")
    assert g.overrides[("_glycoSearchParameters", "GlycoSearchType")] == "NGlycanSearch"
