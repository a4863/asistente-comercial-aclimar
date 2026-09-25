from typing import Protocol


class CredentialStore(Protocol):
    def get_secret(self, service: str, account: str) -> str | None: ...

    def credential_presence(self, service: str, account: str) -> str: ...


class KeyringCredentialStore:
    def get_secret(self, service: str, account: str) -> str | None:
        import keyring

        return keyring.get_password(service, account)

    def credential_presence(self, service: str, account: str) -> str:
        """Return only a bounded state; never pass a secret to the status layer."""
        try:
            secret = self.get_secret(service, account)
            if secret is None or secret == "":
                return "missing"
            return "present" if isinstance(secret, str) else "unavailable"
        except Exception:
            return "unavailable"
        finally:
            secret = None

    def set_secret(self, service: str, account: str, secret: str) -> str:
        """Store a nonempty secret only in keyring; never surface backend details."""
        if not isinstance(secret, str) or not secret.strip():
            return "invalid_secret"
        try:
            import keyring

            keyring.set_password(service, account, secret)
            return "stored"
        except Exception:
            return "unavailable"

    def delete_secret(self, service: str, account: str) -> str:
        """Delete only the named keyring entry; repeated absence is bounded."""
        presence = self.credential_presence(service, account)
        if presence == "missing":
            return "missing"
        if presence != "present":
            return "unavailable"
        try:
            import keyring

            keyring.delete_password(service, account)
            return "deleted"
        except Exception:
            return "unavailable"
