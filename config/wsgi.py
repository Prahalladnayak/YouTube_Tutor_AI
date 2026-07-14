"""
WSGI config for guide_tube project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os

# Apply IPv6 bypass patch to fix ISP WinError 10060 connection timeout issues
try:
    from backend.utils.network import patch_ipv6_bypass
    patch_ipv6_bypass()
except Exception as e:
    print(f"Warning: Could not apply IPv6 patch: {e}")

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = get_wsgi_application()
