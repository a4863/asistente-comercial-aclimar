"""Offline checks for the process-local commercial gate."""

import threading

from app.security.activation import CommercialActivationGate


def test_gate_defaults_off_and_new_instance_does_not_inherit_authorization():
    gate = CommercialActivationGate()
    assert gate.is_enabled is False
    gate.enable()
    assert gate.is_enabled is True
    assert CommercialActivationGate().is_enabled is False


def test_gate_disable_revokes_authorization():
    gate = CommercialActivationGate()
    gate.enable()
    gate.disable()
    assert gate.is_enabled is False
    gate.enable()
    assert gate.is_enabled is True
    gate.disable()
    assert gate.is_enabled is False


def test_gate_concurrent_read_write_has_bounded_boolean_state():
    gate = CommercialActivationGate()
    start = threading.Event()
    observations = []

    def writer():
        assert start.wait(timeout=5)
        for _ in range(500):
            gate.enable()
            gate.disable()

    def reader():
        assert start.wait(timeout=5)
        for _ in range(500):
            observations.append(gate.is_enabled)

    threads = [threading.Thread(target=writer), threading.Thread(target=reader)]
    for thread in threads:
        thread.start()
    start.set()
    for thread in threads:
        thread.join(timeout=5)
        assert not thread.is_alive()
    assert len(observations) == 500
    assert all(type(value) is bool for value in observations)
    assert gate.is_enabled is False
