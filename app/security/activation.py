"""Revocable, process-local commercial authorization; never persisted."""

from threading import Lock


class CommercialActivationGate:
    """Defaults OFF; technical provider configuration does not enable it."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._enabled = False

    @property
    def is_enabled(self) -> bool:
        with self._lock:
            return self._enabled

    def enable(self) -> None:
        with self._lock:
            self._enabled = True

    def disable(self) -> None:
        with self._lock:
            self._enabled = False
