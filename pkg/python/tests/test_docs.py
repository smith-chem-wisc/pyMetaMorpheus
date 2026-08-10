"""Every public capability must be visible on every surface a stranger reads first.

The docs site is docs-as-code: it is built, linked and ``--strict``-checked in CI, so a stale page
announces itself. READMEs are checked by nothing. That asymmetry is not theoretical — when this
test was written the guides documented ``xl_search``, ``run_toml``, ``available_parameters``,
label-free quantification and spectral-library generation, while the repository README, the PyPI
README and the docs landing page described "the four task types" and mentioned none of the five.
Features had shipped, been tested and been documented, and were invisible to anyone who had not
read the source.

The check is deliberately **coarse**: it asserts a capability is *mentioned*, never how it is
worded. A test that pins prose fails on every rewording and teaches people to edit the test until
it passes, which is worse than no test at all.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import pymetamorpheus


def _repo_root():
    """The source checkout, or None when running against an installed wheel.

    Anchored on a directory holding BOTH ``.github/`` and ``README.md``. Walking up to the
    *nearest* README would stop at ``pkg/python/README.md`` and silently check one surface twice
    while never seeing the repository root.
    """
    for parent in Path(__file__).resolve().parents:
        if (parent / ".github").is_dir() and (parent / "README.md").is_file():
            return parent
    return None


ROOT = _repo_root()

pytestmark = pytest.mark.skipif(
    ROOT is None,
    reason="not a source checkout (no directory with both .github/ and README.md above the tests)",
)

# The three surfaces a stranger meets before any guide: the repository front page, the page PyPI
# renders from the packaged README, and the documentation landing page.
SURFACES = ("README.md", "pkg/python/README.md", "docs/index.md")

# Names exported from the package that these surfaces need not spell out.
EXEMPT = {
    "__version__",
    # Task builders exist to be handed to pipeline(), and the pipeline example shows the shape.
    # Naming all five would add noise without telling a reader anything the pipeline row does not.
    "make_search_task",
    "make_calibration_task",
    "make_gptmd_task",
    "make_glyco_search_task",
    "make_xl_search_task",
    "task_from_toml",
    # Types and errors, reached through the reference rather than the front page.
    "Task",
    "RunResult",
    "TaskResult",
    "PyMetaMorpheusError",
    "UsageError",
    "RunError",
    "MetaMorpheusNotFoundError",
}

# Capabilities that are parameters rather than exported names, so nothing in __all__ would catch
# them going undocumented. Each is satisfied by any one of its spellings.
PARAMETER_CAPABILITIES = {
    "label-free quantification": ("quantif",),
    "spectral library generation": ("spectral librar", "write_spectral_library"),
}


def _required_names():
    return sorted(n for n in pymetamorpheus.__all__ if n not in EXEMPT)


def _read(surface: str) -> str:
    return (ROOT / surface).read_text(encoding="utf-8").lower()


@pytest.mark.parametrize("surface", SURFACES)
def test_surface_exists(surface):
    assert (ROOT / surface).is_file(), f"{surface} is missing"


@pytest.mark.parametrize("surface", SURFACES)
def test_every_public_name_is_mentioned(surface):
    """A verb added to __all__ but not to these pages fails here, which is the whole point.

    The list is derived from the package rather than hand-maintained, so it cannot fall behind the
    code the way a duplicated list would.
    """
    text = _read(surface)
    missing = [name for name in _required_names() if name.lower() not in text]
    assert not missing, (
        f"{surface} never mentions: {', '.join(missing)}. "
        "Add it to the capability table, or add it to EXEMPT here with the reason."
    )


@pytest.mark.parametrize("surface", SURFACES)
def test_parameter_capabilities_are_mentioned(surface):
    text = _read(surface)
    missing = [
        capability
        for capability, spellings in PARAMETER_CAPABILITIES.items()
        if not any(s in text for s in spellings)
    ]
    assert not missing, f"{surface} never mentions: {', '.join(missing)}"


def test_the_two_readmes_agree_on_what_the_package_can_do():
    """The repository README and the packaged one are separate files with the same job.

    They were byte-identical when this was written. They need not stay identical — but a capability
    reaching one and not the other is exactly how the PyPI page ended up three features behind the
    GitHub page on the sibling project.
    """
    repo = _read("README.md")
    packaged = _read("pkg/python/README.md")
    names = _required_names() + list(PARAMETER_CAPABILITIES)
    disagreements = []
    for name in names:
        spellings = PARAMETER_CAPABILITIES.get(name, (name.lower(),))
        in_repo = any(s in repo for s in spellings)
        in_packaged = any(s in packaged for s in spellings)
        if in_repo != in_packaged:
            disagreements.append(
                f"{name} ({'repo only' if in_repo else 'packaged only'})"
            )
    assert not disagreements, "READMEs disagree about: " + ", ".join(disagreements)


def test_no_version_number_in_prose():
    """Nothing regenerates or tests a version written into prose, so it can only go stale.

    Matches an x.y.z on the three surfaces. Tolerates Python versions (3.9, 3.12) and the
    MetaMorpheus release line, which are statements about other projects' supported ranges rather
    than a claim about this package's own version.
    """
    import re

    # Three-component versions only; two-component numbers are Python releases.
    pattern = re.compile(r"\b\d+\.\d+\.\d+[\w.]*\b")
    allowed = {"1.1.7"}  # the MetaMorpheus release line, discussed as upstream context
    offenders = {}
    for surface in SURFACES:
        found = {
            m for m in pattern.findall(_read(surface)) if m not in allowed
        }
        if found:
            offenders[surface] = sorted(found)
    assert not offenders, (
        f"version numbers written into prose: {offenders}. "
        "State where the value lives instead of restating it."
    )
