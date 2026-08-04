"""Typed, path-first results (gap G-parse, Option 1).

MetaMorpheus writes standard mzLib result files into a run directory, one
subfolder per task: ``Task1CalibrationTask/``, ``Task2GptmdTask/``,
``Task3SearchTask/``, ``Task1GlycoSearchTask/`` … Each holds ``.psmtsv`` /
``.tsv`` / ``.mzID`` / ``.xml`` outputs.

Following decision G-parse Option 1 we return **paths plus a thin typed object**,
not parsed tables. The output files *are* mzLib result files, which pyMzLib's
readers already parse — so rich tables come from composing with pyMzLib as an
optional extra (Option 2), never from re-implementing parsing here (that would be
anti-parity; the mainland owns the format).

Note the TSV, not CSV convention (D11) — MetaMorpheus already writes TSV.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class TaskResult:
    """One task's output subfolder within a run directory."""

    #: Task type as MetaMorpheus names the folder, e.g. "SearchTask".
    task_type: str
    #: The ``TaskNTypeTask`` directory MetaMorpheus created.
    directory: Path
    #: 1-based position of this task in the run.
    index: int

    def file(self, name: str) -> Path | None:
        """Return ``directory/name`` if it exists, else ``None``."""
        p = self.directory / name
        return p if p.exists() else None

    def glob(self, pattern: str) -> list[Path]:
        """Files in this task's directory matching ``pattern`` (sorted)."""
        return sorted(self.directory.glob(pattern))

    # -- Convenience accessors for the common outputs. Each returns None when the
    #    file isn't present for this task type, so callers can duck-type. --

    @property
    def all_psms(self) -> Path | None:
        """``AllPSMs.psmtsv`` — every peptide-spectrum match (Search)."""
        return self.file("AllPSMs.psmtsv")

    @property
    def all_peptides(self) -> Path | None:
        """``AllPeptides.psmtsv`` — peptide-level results (Search)."""
        return self.file("AllPeptides.psmtsv")

    @property
    def all_proteins(self) -> Path | None:
        """``AllQuantifiedProteinGroups.tsv`` — protein groups (Search + LFQ)."""
        return self.file("AllQuantifiedProteinGroups.tsv")

    @property
    def quantified_proteins(self) -> Path | None:
        """Alias for :attr:`all_proteins` — FlashLFQ protein-group intensities."""
        return self.file("AllQuantifiedProteinGroups.tsv")

    @property
    def quantified_peptides(self) -> Path | None:
        """``AllQuantifiedPeptides.tsv`` — FlashLFQ peptide intensities (Search)."""
        return self.file("AllQuantifiedPeptides.tsv")

    @property
    def quantified_peaks(self) -> Path | None:
        """``AllQuantifiedPeaks.tsv`` — FlashLFQ per-peak quantification (Search)."""
        return self.file("AllQuantifiedPeaks.tsv")

    @property
    def spectral_library(self) -> list[Path]:
        """Spectral libraries written by the search (``*.msp``), when
        ``write_spectral_library=True`` was passed to :func:`search`."""
        return self.glob("*.msp")

    @property
    def mzid(self) -> list[Path]:
        """Any ``.mzID`` identification files."""
        return self.glob("*.mzID")

    @property
    def calibrated_spectra(self) -> list[Path]:
        """Calibrated ``*-calib.mzML`` files (Calibration task)."""
        return self.glob("*-calib.mzML")

    @property
    def gptmd_database(self) -> list[Path]:
        """GPTMD-augmented protein databases (``*GPTMD.xml``)."""
        return self.glob("*GPTMD.xml")

    @property
    def glyco_psms(self) -> list[Path]:
        """Glyco PSM outputs (GlycoSearch task)."""
        return self.glob("*.psmtsv")


@dataclass
class RunResult:
    """The outcome of one MetaMorpheus run (one or more chained tasks).

    ``output_dir`` is the folder passed to ``-o``. ``tasks`` are the per-task
    result folders in run order. The raw process output is kept for diagnostics.
    """

    output_dir: Path
    tasks: list[TaskResult] = field(default_factory=list)
    stdout: str = ""
    stderr: str = ""

    def task(self, task_type: str) -> TaskResult | None:
        """Return the (last) task of ``task_type`` (e.g. "SearchTask"), or None."""
        matches = [t for t in self.tasks if t.task_type == task_type]
        return matches[-1] if matches else None

    @property
    def search(self) -> TaskResult | None:
        """The search task's results, if this run included one."""
        return self.task("SearchTask")

    @property
    def calibration(self) -> TaskResult | None:
        return self.task("CalibrationTask")

    @property
    def gptmd(self) -> TaskResult | None:
        return self.task("GptmdTask")

    @property
    def glyco_search(self) -> TaskResult | None:
        return self.task("GlycoSearchTask")


def discover_tasks(output_dir: Path) -> list[TaskResult]:
    """Find ``TaskN<Type>Task`` subfolders in ``output_dir``, ordered by N.

    MetaMorpheus names each task folder ``Task<index><TaskType>`` (e.g.
    ``Task3SearchTask``). We parse the leading ``Task<int>`` prefix for ordering
    and take the remainder as the task type.
    """
    results: list[TaskResult] = []
    for child in output_dir.iterdir():
        if not child.is_dir():
            continue
        name = child.name
        if not name.startswith("Task"):
            continue
        rest = name[len("Task"):]
        digits = ""
        for ch in rest:
            if ch.isdigit():
                digits += ch
            else:
                break
        if not digits:
            continue
        index = int(digits)
        task_type = rest[len(digits):]  # e.g. "SearchTask"
        results.append(TaskResult(task_type=task_type, directory=child, index=index))
    results.sort(key=lambda t: t.index)
    return results
