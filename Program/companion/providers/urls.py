"""URL checks copied from prosperos-study server/providers/config.py at bbcbde4."""
from ipaddress import ip_address
from urllib.parse import urlsplit

from companion.errors import DomainError


def is_loopback(host: str | None) -> bool:
    if host == 'localhost':
        return True
    try:
        return ip_address(host or '').is_loopback
    except ValueError:
        return False


def validate_compatible_url(url: str):
    parts = urlsplit(url)
    if not parts.hostname or (parts.scheme != 'https' and not (parts.scheme == 'http' and is_loopback(parts.hostname))):
        raise DomainError('Use an HTTPS API base URL, or HTTP for a loopback service.', 422)
    if any((parts.username, parts.password, parts.query, parts.fragment)):
        raise DomainError('Put credentials in the API key field, not in the server address.', 422)
    if parts.port == 0:
        raise DomainError('Use a valid service port.', 422)
