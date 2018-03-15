from __future__ import unicode_literals
from django.conf import settings
from urllib.parse import urljoin

# These are required for SSO to function. Can be left blank if settings.DEBUG is set to True
CLIENT_ID = getattr(settings, 'ESI_SSO_CLIENT_ID', None)
CLIENT_SECRET = getattr(settings, 'ESI_SSO_CLIENT_SECRET', None)
CALLBACK_URL = getattr(settings, 'ESI_SSO_CALLBACK_URL', None)

# This determines how long a redirect is remembered
CALLBACK_TIMEOUT = getattr(settings, 'ESI_CALLBACK_TIMEOUT', 300)

# Change these to switch to Singularity
API_DATASOURCE = getattr(settings, 'ESI_API_DATASOURCE', 'tranquility').lower()
OAUTH_URL = getattr(settings, 'ESI_SSO_BASE_URL', 'https://login.eveonline.com/oauth/')

# Define the base template to extend
BASE_TEMPLATE = getattr(settings, 'ESI_BASE_TEMPLATE', 'public/base.html')

# Enable to force new token creation every callback
ALWAYS_CREATE_TOKEN = getattr(settings, 'ESI_ALWAYS_CREATE_TOKEN', False)

# Disable to stop caching endpoint responses
CACHE_RESPONSE = getattr(settings, 'ESI_CACHE_RESPONSE', True)

# These probably won't ever change. Override if needed.
API_URL = getattr(settings, 'ESI_API_URL', 'https://esi.tech.ccp.is/')
OAUTH_LOGIN_URL = getattr(settings, 'ESI_SSO_LOGIN_URL', urljoin(OAUTH_URL, "authorize/"))
TOKEN_URL = getattr(settings, 'ESI_CODE_EXCHANGE_URL', urljoin(OAUTH_URL, "token/"))
TOKEN_VERIFY_URL = getattr(settings, 'ESI_TOKEN_EXCHANGE_URL', urljoin(OAUTH_URL, "verify/"))
TOKEN_VALID_DURATION = int(getattr(settings, 'ESI_TOKEN_VALID_DURATION', 1200))

