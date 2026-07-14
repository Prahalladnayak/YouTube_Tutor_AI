#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    # Apply IPv6 bypass patch to fix ISP WinError 10060 connection timeout issues
    try:
        from backend.utils.network import patch_ipv6_bypass
        patch_ipv6_bypass()
    except Exception as e:
        print(f"Warning: Could not apply IPv6 patch: {e}")

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
