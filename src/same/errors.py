"""SAME runtime exceptions."""

from __future__ import annotations


class SameError(Exception):
    """Base class for recoverable SAME tooling and runtime errors."""


class AbiError(SameError):
    """A service packet or generated ABI is invalid."""


class QueueFullError(SameError):
    """A fail-closed event queue has no free slot."""


class TargetValidationError(SameError):
    """A legacy machine-target manifest violates the SAME contract."""


class PackageFormatError(SameError):
    """A SAME package is malformed or fails integrity checks."""


class DonorError(SameError):
    """A donor repository cannot be identified or imported safely."""


class EngineError(SameError):
    """Base class for engine-host failures."""


class EngineRegistrationError(EngineError):
    """An engine could not be registered in an engine registry."""


class EngineLifecycleError(EngineError):
    """An engine lifecycle method was invoked in an invalid state."""


class EngineCompatibilityError(EngineError):
    """An engine or game profile cannot run with the available services."""


class EngineExecutionError(EngineError):
    """An engine failed while executing game logic."""


class ProfileValidationError(EngineError):
    """An engine game-profile manifest is invalid."""


class ResourceError(EngineError):
    """A required engine resource is missing, ambiguous, or corrupt."""


class SaveFormatError(EngineError):
    """A SAME engine save envelope is invalid or incompatible."""
