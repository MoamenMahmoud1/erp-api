import ipaddress
import socket

from django.conf import settings


def normalize_ip(value):
    try:
        return str(ipaddress.ip_address(value))
    except (TypeError, ValueError):
        return None


def _resolved_host_ips(hostname):
    try:
        return {
            str(ipaddress.ip_address(result[4][0]))
            for result in socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
        }
    except (OSError, ValueError):
        return set()


def is_trusted_proxy(ip_value):
    address = normalize_ip(ip_value)
    if address is None:
        return False

    explicit_networks = getattr(settings, "TRUSTED_PROXY_IPS", ())
    for value in explicit_networks:
        try:
            if ipaddress.ip_address(address) in ipaddress.ip_network(value, strict=False):
                return True
        except ValueError:
            continue

    for hostname in getattr(settings, "TRUSTED_PROXY_HOSTS", ()):
        if address in _resolved_host_ips(hostname):
            return True

    return False
