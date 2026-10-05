"""OS credential vault under the Companion's own service name.

Adapted from prosperos-study server/providers/vault.py at bbcbde4. The service name and
environment fallback differ so the two products never read each other's keys.
"""
import os
from typing import Protocol

from companion.errors import DomainError
from companion.identity import CREDENTIAL_SERVICE

ENV_KEY = 'COMPANION_API_KEY'


class CredentialVault(Protocol):
    def get(self, reference: str) -> str | None: ...
    def put(self, reference: str, secret: str) -> None: ...


class SystemVault:
    service = CREDENTIAL_SERVICE

    def get(self, reference: str) -> str | None:
        import keyring
        from keyring.errors import KeyringError
        try:
            return keyring.get_password(self.service, reference)
        except KeyringError as error:
            raise DomainError('The OS credential vault is unavailable. Check your keyring setup.', 503) from error

    def put(self, reference: str, secret: str) -> None:
        import keyring
        from keyring.errors import KeyringError
        try:
            keyring.set_password(self.service, reference, secret)
        except KeyringError as error:
            raise DomainError('Could not save the key in the OS credential vault.', 503) from error


class MemoryVault:
    """In-process vault for tests and for systems without a keyring."""

    def __init__(self):
        self.secrets = {}

    def get(self, reference: str) -> str | None:
        return self.secrets.get(reference)

    def put(self, reference: str, secret: str) -> None:
        self.secrets[reference] = secret


def credential_for(vault: CredentialVault, reference: str | None) -> str | None:
    if reference:
        return vault.get(reference)
    return os.environ.get(ENV_KEY)
