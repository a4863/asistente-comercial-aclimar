"""Offline Windows subprocess coverage for the operational lock primitive."""

import os
from pathlib import Path
import subprocess
import sys
import threading
import time

import pytest

from app.security.single_instance import SingleInstanceError, SingleInstanceLock


@pytest.fixture
def synthetic_db(isolated_tmp_path):
    if sys.platform != "win32":
        pytest.skip("Windows operational lock")
    path = isolated_tmp_path / "assistant.db"
    path.write_bytes(b"synthetic, not a production database")
    return path


_HOLDER = """
import pathlib, sys
from app.security.single_instance import SingleInstanceLock
lock = SingleInstanceLock(sys.argv[1]).acquire()
pathlib.Path(sys.argv[2]).write_text('ready', encoding='ascii')
sys.stdin.readline()
lock.close()
"""


def _start_holder(database: Path, marker: Path) -> subprocess.Popen:
    process = subprocess.Popen(
        [sys.executable, "-c", _HOLDER, str(database), str(marker)],
        stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
        text=True,
    )
    deadline = time.monotonic() + 5
    while not marker.exists() and time.monotonic() < deadline:
        if process.poll() is not None:
            break
        time.sleep(0.02)
    if not marker.exists():
        process.kill()
        _, errors = process.communicate(timeout=5)
        pytest.fail(f"holder did not acquire lock: {errors[-500:]}")
    return process


def _stop(process: subprocess.Popen, *, force: bool = False) -> None:
    if process.poll() is None:
        if force:
            process.kill()
        else:
            assert process.stdin is not None
            process.stdin.write("\n")
            process.stdin.flush()
    try:
        process.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.communicate(timeout=5)
        pytest.fail("holder did not exit within timeout")


def test_equivalent_relative_absolute_and_cwd_aliases(synthetic_db, monkeypatch):
    root = synthetic_db.parent
    subdir = root / "nested"
    subdir.mkdir()
    monkeypatch.chdir(root)
    relative = SingleInstanceLock("sqlite:///assistant.db")
    absolute = SingleInstanceLock(synthetic_db)
    monkeypatch.chdir(subdir)
    from_other_cwd = SingleInstanceLock("../assistant.db")
    assert relative.database_identity == absolute.database_identity == from_other_cwd.database_identity
    assert relative.sidecar_path == absolute.sidecar_path == from_other_cwd.sidecar_path
    other = root / "other.db"
    other.write_bytes(b"synthetic")
    assert SingleInstanceLock(other).sidecar_path != relative.sidecar_path


@pytest.mark.parametrize("identity", [
    "postgresql:///data.db", "sqlite:///:memory:", "sqlite:///data.db?uri=true",
    "file:data.db", "sqlite:///missing.db", "sqlite://", "sqlite:////server/share/db",
])
def test_unsupported_database_forms_fail_closed(synthetic_db, identity):
    with pytest.raises(SingleInstanceError):
        SingleInstanceLock(identity)


def test_second_process_refused_then_normal_release_and_stale_filename(synthetic_db):
    marker = synthetic_db.parent / "holder-ready"
    process = _start_holder(synthetic_db, marker)
    try:
        contender = SingleInstanceLock(synthetic_db)
        with pytest.raises(SingleInstanceError) as error:
            contender.acquire()
        assert error.value.code == "already_locked"
        assert not contender.is_owner
        other = synthetic_db.parent / "other.db"
        other.write_bytes(b"synthetic")
        with SingleInstanceLock(other) as independent:
            assert independent.is_owner
    finally:
        _stop(process)
    with SingleInstanceLock(synthetic_db) as replacement:
        assert replacement.is_owner
        assert replacement.sidecar_path.exists()
    # The filename persists but is not ownership evidence.
    with SingleInstanceLock(synthetic_db) as again:
        assert again.is_owner


def test_forced_process_exit_releases_exclusive_handle(synthetic_db):
    process = _start_holder(synthetic_db, synthetic_db.parent / "kill-ready")
    try:
        with pytest.raises(SingleInstanceError):
            SingleInstanceLock(synthetic_db).acquire()
    finally:
        _stop(process, force=True)
    deadline = time.monotonic() + 5
    while True:
        try:
            replacement = SingleInstanceLock(synthetic_db).acquire()
            break
        except SingleInstanceError as error:
            assert error.code == "already_locked" and time.monotonic() < deadline
            time.sleep(0.02)
    try:
        assert replacement.is_owner
    finally:
        replacement.close()


def test_thread_independent_ownership_noninheritance_and_repeated_close(synthetic_db):
    lock = SingleInstanceLock(synthetic_db).acquire()
    assert lock.is_owner
    assert not os.get_handle_inheritable(lock._handle)
    observed: list[bool] = []
    thread = threading.Thread(target=lambda: observed.append(lock.is_owner))
    thread.start()
    thread.join(timeout=2)
    assert not thread.is_alive() and observed == [True]
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(3)"],
                             close_fds=False)
    try:
        lock.close()
        assert not lock.is_owner
        lock.close()
        assert child.poll() is None
        with SingleInstanceLock(synthetic_db) as replacement:
            assert replacement.is_owner
    finally:
        child.kill()
        child.wait(timeout=5)


@pytest.mark.skipif(sys.platform == "win32", reason="non-Windows behavior only")
def test_non_windows_fails_closed(isolated_tmp_path):
    with pytest.raises(SingleInstanceError, match="unsupported_platform"):
        SingleInstanceLock(isolated_tmp_path / "synthetic.db")
