from typing import Protocol


class CredentialStore(Protocol):
    def get_secret(self, service: str, account: str) -> str | None: ...


class KeyringCredentialStore:
    def get_secret(self, service: str, account: str) -> str | None:
        import keyring

        return keyring.get_password(service, account)
