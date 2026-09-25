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
