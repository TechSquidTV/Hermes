"""Public-network URL validation shared by the API and worker transport."""

import ipaddress
import socket
from typing import cast
from urllib.parse import urlsplit

SocketInfo = tuple[
    socket.AddressFamily,
    socket.SocketKind,
    int,
    str,
    tuple[str, int] | tuple[str, int, int, int],
]


def public_addresses(host: str, port: int) -> list[SocketInfo]:
    """Resolve once and reject the entire answer if any address is non-public."""
    try:
        addresses = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except OSError as error:
        raise ValueError("URL host could not be resolved") from error
    if not addresses:
        raise ValueError("URL host could not be resolved")
    for family, _, _, _, address in addresses:
        if family not in {socket.AF_INET, socket.AF_INET6}:
            raise ValueError("URL must resolve to an IP address")
        ip = ipaddress.ip_address(address[0])
        if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
            ip = ip.ipv4_mapped
        if (
            not ip.is_global
            or ip.is_multicast
            or ip.is_reserved
            or (isinstance(ip, ipaddress.IPv6Address) and ip.is_site_local)
        ):
            raise ValueError("URL must resolve only to public IP addresses")
    return cast(list[SocketInfo], addresses)


def validate_public_url(url: str, *, resolve: bool = True) -> str:
    """Require a bounded HTTP(S) URL without embedded credentials."""
    if len(url) > 2048 or any(ord(character) < 33 for character in url):
        raise ValueError("Invalid URL")
    try:
        parsed = urlsplit(url)
        host = parsed.hostname
        port = parsed.port
    except ValueError as error:
        raise ValueError("Invalid URL") from error
    if parsed.scheme not in {"http", "https"} or not host:
        raise ValueError("URL must use HTTP or HTTPS and include a host")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("URL must not include credentials")
    if resolve:
        public_addresses(host, port or (443 if parsed.scheme == "https" else 80))
    return url
