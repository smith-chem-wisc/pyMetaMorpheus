"""Shared pytest fixtures / markers for pyMetaMorpheus.

Offline tests run everywhere (no MetaMorpheus needed). The ``live`` marker gates
tests that invoke the real CLI; they self-skip unless ``PYMM_METAMORPHEUS`` is set
and points at a runnable executable — the same env var the runner uses.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from pymetamorpheus._errors import MetaMorpheusNotFoundError
from pymetamorpheus._runner import locate_cli


def _cli_available() -> bool:
    """True if the runner can find a CLI — via PYMM_METAMORPHEUS or the staged
    payload (the same resolution real calls use), so the live CI job that stages
    a self-contained payload without setting the env var is still exercised."""
    try:
        locate_cli()
        return True
    except MetaMorpheusNotFoundError:
        return False


@pytest.fixture(scope="session")
def cli_or_skip():
    if not _cli_available():
        pytest.skip("PYMM_METAMORPHEUS not set to a runnable MetaMorpheus CLI")


@pytest.fixture(scope="session")
def sample_data():
    """Bundled MetaMorpheus test data, if present in the pinned checkout."""
    data = Path(
        os.environ.get(
            "PYMM_SAMPLE_DATA",
            r"E:\GitClones\MetaMorpheus\MetaMorpheus\EngineLayer\Data",
        )
    )
    spectra = data / "SmallCalibratible_Yeast.mzML"
    db = data / "SmallYeast.fasta"
    if not (spectra.exists() and db.exists()):
        pytest.skip(f"sample data not found under {data}")
    return {"spectra": spectra, "database": db}
