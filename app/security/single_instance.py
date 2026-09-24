"""Windows-only, process-held exclusive handle for one local SQLite database."""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import stat
import sys
import threading

from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError


class SingleInstanceError(RuntimeError):
    """A bounded, path-free lock failure."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _database_path(database: str | Path) -> Path:
    if sys.platform != "win32":
        raise SingleInstanceError("unsupported_platform")
    if isinstance(database, Path):
        raw = str(database)
    elif isinstance(database, str) and database and "\x00" not in database:
        raw = database
    else:
        raise SingleInstanceError("invalid_database_identity")
    if raw.startswith("file:"):
        raise SingleInstanceError("unsupported_database_identity")
    if "://" in raw:
        try:
            url = make_url(raw)
        except (ArgumentError, ValueError):
            raise SingleInstanceError("unsupported_database_identity") from None
        if (url.drivername not in {"sqlite", "sqlite+pysqlite"} or
                url.username is not None or url.password is not None or
                url.host is not None or url.port is not None or url.query or
                not url.database or url.database == ":memory:"):
            raise SingleInstanceError("unsupported_database_identity")
        raw = url.database
    if (not raw or raw.startswith(("\\\\", "//", "\\\\?\\", "\\\\.\\")) or
            raw.startswith("/") or "?" in raw or "#" in raw):
        raise SingleInstanceError("unsupported_database_identity")
    candidate = Path(raw)
    if (candidate.drive and not candidate.root) or os.path.isreserved(candidate.name):
        raise SingleInstanceError("unsupported_database_identity")
    try:
        resolved = candidate.resolve(strict=True)
        info = resolved.stat()
    except FileNotFoundError:
        try:
            if candidate.is_symlink():
                raise SingleInstanceError("unsupported_database_identity")
            parent = candidate.parent.resolve(strict=True)
            if not parent.is_dir():
                raise SingleInstanceError("invalid_database_identity")
            resolved = parent / candidate.name
        except (OSError, RuntimeError, ValueError):
            raise SingleInstanceError("invalid_database_identity") from None
        info = None
    except (OSError, RuntimeError, ValueError):
        raise SingleInstanceError("invalid_database_identity") from None
    if (not resolved.is_absolute() or not resolved.drive or not resolved.root or
            (info is not None and (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1))):
        raise SingleInstanceError("unsupported_database_identity")
    if _kernel32.GetDriveTypeW(resolved.anchor) != 3:  # DRIVE_FIXED
        raise SingleInstanceError("unsupported_storage")
    return Path(os.path.normcase(str(resolved)))


if sys.platform == "win32":
    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _kernel32.GetDriveTypeW.argtypes = [wintypes.LPCWSTR]
    _kernel32.GetDriveTypeW.restype = wintypes.UINT
    _kernel32.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                      ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD,
                                      wintypes.HANDLE]
    _kernel32.CreateFileW.restype = wintypes.HANDLE
    _kernel32.GetHandleInformation.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    _kernel32.GetHandleInformation.restype = wintypes.BOOL
    _kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    _kernel32.CloseHandle.restype = wintypes.BOOL


class SingleInstanceLock:
    """Owns one non-inheritable Win32 file handle until explicit close."""

    def __init__(self, database: str | Path):
        canonical = _database_path(database)
        self.database_identity = canonical
        self.sidecar_path = Path(f"{canonical}.aclimar.lock")
        self._handle: int | None = None
        self._pid = os.getpid()
        self._guard = threading.Lock()

    def acquire(self) -> SingleInstanceLock:
        with self._guard:
            if self._handle is not None:
                raise SingleInstanceError("already_owned")
            handle = _kernel32.CreateFileW(
                str(self.sidecar_path), 0xC0000000, 0, None, 4, 0x80, None,
            )  # GENERIC_READ|WRITE, no sharing, OPEN_ALWAYS, FILE_ATTRIBUTE_NORMAL
            if handle is None or handle == ctypes.c_void_p(-1).value:
                error = ctypes.get_last_error()
                raise SingleInstanceError("already_locked" if error == 32 else "lock_unavailable")
            flags = wintypes.DWORD()
            if (not _kernel32.GetHandleInformation(handle, ctypes.byref(flags)) or
                    flags.value & 0x1):  # HANDLE_FLAG_INHERIT must be clear.
                _kernel32.CloseHandle(handle)
                raise SingleInstanceError("lock_unavailable")
            self._handle = handle
            self._pid = os.getpid()
        return self

    @property
    def is_owner(self) -> bool:
        with self._guard:
            if self._handle is None or self._pid != os.getpid():
                return False
            flags = wintypes.DWORD()
            return bool(_kernel32.GetHandleInformation(self._handle, ctypes.byref(flags))) and not (
                flags.value & 0x1)

    def close(self) -> None:
        with self._guard:
            handle, self._handle = self._handle, None
            if handle is not None and self._pid == os.getpid():
                if not _kernel32.CloseHandle(handle):
                    raise SingleInstanceError("release_failed")

    def __enter__(self) -> SingleInstanceLock:
        return self.acquire()

    def __exit__(self, *_exc: object) -> None:
        self.close()
