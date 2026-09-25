"""Local interactive management of the configured AI keyring entry."""

import getpass
import sys

from app.config import load_operational_settings
from app.security.credentials import KeyringCredentialStore


_USAGE = "Usage: asistente-aclimar-credential {set|status|delete}"


def main(argv: list[str] | None = None) -> int:
    arguments = sys.argv[1:] if argv is None else argv
    if arguments == ["--help"]:
        print(_USAGE)
        return 0
    if len(arguments) != 1 or arguments[0] not in {"set", "status", "delete"}:
        print("invalid_command", file=sys.stderr)
        return 2
    action = arguments[0]
    try:
        ai = load_operational_settings().ai
        store = KeyringCredentialStore()
    except Exception:
        print("unavailable")
        return 1
    service, account = ai.credential_service, ai.credential_account

    if action == "status":
        try:
            result = store.credential_presence(service, account)
        except Exception:
            result = "unavailable"
        if result not in {"present", "missing", "unavailable"}:
            result = "unavailable"
        print(result)
        return 0 if result != "unavailable" else 1

    if action == "delete":
        try:
            result = store.delete_secret(service, account)
        except Exception:
            result = "unavailable"
        if result not in {"deleted", "missing", "unavailable"}:
            result = "unavailable"
        print(result)
        return 0 if result != "unavailable" else 1

    if not sys.stdin.isatty():
        print("interactive_terminal_required")
        return 1
    try:
        secret = getpass.getpass("OpenAI API key: ")
    except (Exception, KeyboardInterrupt):
        print("unavailable")
        return 1
    if not isinstance(secret, str) or not secret.strip():
        print("invalid_secret")
        return 1
    try:
        result = store.set_secret(service, account, secret)
    except Exception:
        result = "unavailable"
    finally:
        secret = None
    if result not in {"stored", "invalid_secret", "unavailable"}:
        result = "unavailable"
    print(result)
    return 0 if result == "stored" else 1


if __name__ == "__main__":
    raise SystemExit(main())
