from __future__ import unicode_literals
from django.conf import settings

# These are required for SSO to function. Can be left blank if settings.DEBUG is set to True
ESI_SSO_CLIENT_ID = getattr(settings, 'ESI_SSO_CLIENT_ID', None)
ESI_SSO_CLIENT_SECRET = getattr(settings, 'ESI_SSO_CLIENT_SECRET', None)
ESI_SSO_CALLBACK_URL = getattr(settings, 'ESI_SSO_CALLBACK_URL', None)

# Change these to switch to Singularity
ESI_API_DATASOURCE = getattr(settings, 'ESI_API_DATASOURCE', 'tranquility')
ESI_OAUTH_URL = getattr(settings, 'ESI_SSO_BASE_URL', 'https://login.eveonline.com/oauth')

# Change this to access different revisions of the ESI API by default
ESI_API_VERSION = getattr(settings, 'ESI_API_VERSION', 'latest')

# Define the base template to extend
ESI_BASE_TEMPLATE = getattr(settings, 'ESI_BASE_TEMPLATE', 'public/base.html')

# Enable to force new token creation every callback
ESI_ALWAYS_CREATE_TOKEN = getattr(settings, 'ESI_ALWAYS_CREATE_TOKEN', False)

# Disable to stop caching endpoint responses
ESI_CACHE_RESPONSE = getattr(settings, 'ESI_CACHE_RESPONSE', True)

# These probably won't ever change. Override if needed.
ESI_API_URL = getattr(settings, 'ESI_API_URL', 'https://esi.tech.ccp.is/')
ESI_OAUTH_LOGIN_URL = getattr(settings, 'ESI_SSO_LOGIN_URL', ESI_OAUTH_URL + "/authorize/")
ESI_TOKEN_URL = getattr(settings, 'ESI_CODE_EXCHANGE_URL', ESI_OAUTH_URL + "/token")
ESI_TOKEN_VERIFY_URL = getattr(settings, 'ESI_TOKEN_EXCHANGE_URL', ESI_OAUTH_URL + "/verify")
ESI_TOKEN_VALID_DURATION = int(getattr(settings, 'ESI_TOKEN_VALID_DURATION', 1200))
ESI_SPEC_CACHE_DURATION = int(getattr(settings, 'ESI_SPEC_CACHE_DURATION', 3600))
