import ipaddress
import socket
from urllib.parse import urlparse
from typing import Optional
from app.core.logging import get_logger

logger = get_logger(__name__)

BLOCKED_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]


def validate_url(url: str) -> Optional[str]:
    """Validate and normalize a URL. Returns None if invalid."""
    try:
        parsed = urlparse(url)
    except Exception:
        return None

    if parsed.scheme not in ("http", "https"):
        logger.warning(f"Blocked non-http URL: {url}")
        return None

    if not parsed.hostname:
        return None

    return url


def check_ip_not_private(hostname: str) -> bool:
    """Resolve hostname and check it doesn't point to a private/internal IP."""
    try:
        resolved = socket.getaddrinfo(hostname, None)
        for family, _, _, _, sockaddr in resolved:
            ip = ipaddress.ip_address(sockaddr[0])
            for network in BLOCKED_NETWORKS:
                if ip in network:
                    logger.warning(f"Blocked private IP {ip} for hostname {hostname}")
                    return False
        return True
    except (socket.gaierror, ValueError) as e:
        logger.warning(f"Failed to resolve or validate hostname {hostname}: {e}")
        return False


def safe_fetch_url(url: str) -> Optional[str]:
    """Validate URL, check IP safety, and return the URL if safe."""
    validated = validate_url(url)
    if not validated:
        return None

    parsed = urlparse(validated)
    hostname = parsed.hostname
    if not hostname:
        return None

    if not check_ip_not_private(hostname):
        return None

    return validated
