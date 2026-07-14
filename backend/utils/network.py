# backend/utils/network.py
import socket

def patch_ipv6_bypass():
    """
    Force socket DNS resolution to prefer IPv4.
    This resolves socket timeout errors (WinError 10060) caused by broken IPv6 routing from the ISP.
    """
    orig_getaddrinfo = socket.getaddrinfo
    def getaddrinfo_ipv4(host, port, family=0, type=0, proto=0, flags=0):
        # socket.AF_INET forces IPv4
        return orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
    socket.getaddrinfo = getaddrinfo_ipv4
    print("[Network Patch] Applied IPv4-only socket fallback to bypass broken ISP IPv6 routing.")
