import logging
from enum import Enum


logger = logging.getLogger("aclimar.audit")


class AuditCode(str, Enum):
    APPLICATION_STARTED = "application_started"


def record(event: AuditCode) -> None:
    if not isinstance(event, AuditCode):
        raise ValueError("Audit events must use a controlled code")
    logger.info("audit event: %s", event.value)
