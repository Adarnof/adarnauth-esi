from __future__ import unicode_literals
from django.conf import settings

# These are required in your project's settings.
ESI_SSO_CLIENT_ID = getattr(settings, 'ESI_SSO_CLIENT_ID')
ESI_SSO_CLIENT_SECRET = getattr(settings, 'ESI_SSO_CLIENT_SECRET')
ESI_SSO_CALLBACK_URL = getattr(settings, 'ESI_SSO_CALLBACK_URL')

# These probably won't ever change. Override if needed.
ESI_API_URL = getattr(settings, 'ESI_API_URL', 'https://https://esi.tech.ccp.is/')
ESI_API_VERSION = getattr(settings, 'ESI_API_VERSION', 'latest')
ESI_SWAGGER_URL = getattr(settings, 'ESI_SWAGGER_URL', ESI_API_URL + ESI_API_VERSION + '/swagger.json')
ESI_SSO_LOGIN_URL = getattr(settings, 'ESI_SSO_LOGIN_URL', "https://login.eveonline.com/oauth/authorize/")
ESI_CODE_EXCHANGE_URL = getattr(settings, 'ESI_CODE_EXCHANGE_URL', "https://login.eveonline.com/oauth/token")
ESI_TOKEN_EXCHANGE_URL = getattr(settings, 'ESI_TOKEN_EXCHANGE_URL', "https://login.eveonline.com/oauth/verify")
ESI_TOKEN_REFRESH_URL = getattr(settings, 'ESI_TOKEN_REFRESH_URL', "https://login.eveonline.com/oauth/token")
ESI_TOKEN_VALID_DURATION = int(getattr(settings, 'ESI_TOKEN_VALID_DURATION', 1200))
