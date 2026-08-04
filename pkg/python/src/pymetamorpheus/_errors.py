"""Exception hierarchy for pyMetaMorpheus.

Mirrors pyMzLib's error families (usage errors raised *before* the subprocess,
run/protocol errors raised *after* it fails) so the two bindings feel the same.
Everything is a plain ``Exception`` subclass — zero third-party dependencies (D2).
"""

from __future__ import annotations


class PyMetaMorpheusError(Exception):
    """Base class for every error this package raises."""


class UsageError(PyMetaMorpheusError):
    """The caller asked for something impossible before MetaMorpheus ran.

    Raised entirely on the Python side (bad file extension, missing input,
    unknown parameter) *before* the CLI subprocess is launched, so it never
    costs a process spawn. Analogous to pyMzLib's ``UsageError``.
    """


class MetaMorpheusNotFoundError(UsageError):
    """The MetaMorpheus CLI executable could not be located.

    See :func:`pymetamorpheus._runner.locate_cli` for the search order and the
    ``PYMM_METAMORPHEUS`` environment-variable override.
    """


class RunError(PyMetaMorpheusError):
    """MetaMorpheus ran but exited non-zero (or produced no output).

    Carries the process ``returncode`` and the tail of stdout/stderr so the
    caller can see what the engine actually said. Analogous to pyMzLib's
    ``BridgeError`` — the transport layer failed, not the caller's request.
    """

    def __init__(
        self,
        message: str,
        *,
        returncode: int | None = None,
        stdout: str | None = None,
        stderr: str | None = None,
        command: list[str] | None = None,
    ) -> None:
        super().__init__(message)
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.command = command
