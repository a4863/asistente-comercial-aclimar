import logging
logger = logging.getLogger("aclimar.audit")
def record(event: str) -> None: logger.info("audit event: %s", event)
