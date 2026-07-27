import ipaddress

from django.conf import settings


def normalize_ip(value):
    try:
        return str(ipaddress.ip_address(value))
    except (TypeError, ValueError):
        return None


def is_trusted_proxy(ip_value):
    address = ipaddress.ip_address(ip_value)
    for value in getattr(settings, "TRUSTED_PROXY_IPS", ()):
        try:
            if address in ipaddress.ip_network(value, strict=False):
                return True
        except ValueError:
            continue
    return False
