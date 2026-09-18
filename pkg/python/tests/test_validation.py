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


def test_raw_needs_the_licence_argument(tmp_path):
    # Agreeing to Thermo's licence is the caller's act, so .raw is refused without it,
    # and the refusal names the argument that fixes it.
    raw = _touch(tmp_path, "run.raw")
    with pytest.raises(mm.UsageError) as exc:
        _validate_spectra(raw)
    assert "accept_thermo_licence=True" in str(exc.value)


def test_raw_accepted_with_the_licence_argument(tmp_path):
    raw = _touch(tmp_path, "run.RAW")
    assert _validate_spectra(raw, accept_thermo_licence=True) == [raw]


def test_bruker_d_still_rejected(tmp_path):
    with pytest.raises(mm.UsageError) as exc:
        _validate_spectra(tmp_path / "run.d", accept_thermo_licence=True)
    assert "Bruker" in str(exc.value)


def _stub_cli(monkeypatch, tmp_path):
    """Replace the CLI with a recorder: returns the list every invoke's args land in.

    Defaults come from a single SearchTask.toml, and the fake run makes the task
    folder MetaMorpheus would, so run_tasks' "produced nothing" guard is satisfied.
    """
    import subprocess

    from pymetamorpheus import _engine

    calls: list[list[str]] = []

    def fake_defaults(out_dir):
        p = out_dir / "SearchTask.toml"
        p.write_text('TaskType = "Search"\n', encoding="utf-8")
        return {p.name: p}

    def fake_invoke(args, timeout=None):
        calls.append(list(args))
        out = args[args.index("-o") + 1]
        (tmp_path / out / "Task1SearchTask").mkdir(parents=True, exist_ok=True)
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    monkeypatch.setattr(_engine, "locate_cli", lambda: ["CMD"])
    monkeypatch.setattr(_engine, "generate_default_tomls", fake_defaults)
    monkeypatch.setattr(_engine, "invoke", fake_invoke)
    return calls


def test_raw_run_passes_the_flag_and_discloses_it(monkeypatch, tmp_path):
    calls = _stub_cli(monkeypatch, tmp_path)
    raw = _touch(tmp_path, "run.raw")
    db = _touch(tmp_path, "proteins.fasta")
    result = mm.search(raw, db, tmp_path / "out", accept_thermo_licence=True)
    assert "--acceptThermoLicence" in calls[0]
    assert any("RawFileReader" in c for c in result.caveats)


def test_mzml_run_never_agrees_to_anything(monkeypatch, tmp_path):
    # The argument alone must not agree to the licence: only a .raw in the run does.
    calls = _stub_cli(monkeypatch, tmp_path)
    mzml = _touch(tmp_path, "run.mzML")
    db = _touch(tmp_path, "proteins.fasta")
    result = mm.search(mzml, db, tmp_path / "out", accept_thermo_licence=True)
    assert "--acceptThermoLicence" not in calls[0]
    assert result.caveats == []


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


def test_database_gz_must_wrap_supported(tmp_path):
    # proteins.fasta.gz is fine; a bare foo.gz is not.
    ok = _touch(tmp_path, "proteins.fasta.gz")
    assert _validate_databases(ok) == [ok]
    with pytest.raises(mm.UsageError):
        _validate_databases(_touch(tmp_path, "archive.gz"))


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


def test_search_quantification_overrides():
    sp = "SearchParameters"
    # Default: no quant overrides (keep MetaMorpheus's own LFQ-on default).
    assert not any(k[0] == sp for k in mm.make_search_task().overrides)
    t = mm.make_search_task(
        quantify=False, match_between_runs=True, normalize=True, quantify_ppm_tol=10
    )
    assert t.overrides[(sp, "DoLabelFreeQuantification")] is False
    assert t.overrides[(sp, "MatchBetweenRuns")] is True
    assert t.overrides[(sp, "Normalize")] is True
    assert t.overrides[(sp, "QuantifyPpmTol")] == 10.0


def test_search_spectral_library_overrides():
    sp = "SearchParameters"
    # Off by default (no override emitted).
    assert ("SearchParameters", "WriteSpectralLibrary") not in mm.make_search_task().overrides
    t = mm.make_search_task(write_spectral_library=True, update_spectral_library=False)
    assert t.overrides[(sp, "WriteSpectralLibrary")] is True
    assert t.overrides[(sp, "UpdateSpectralLibrary")] is False
