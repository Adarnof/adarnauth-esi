from __future__ import unicode_literals
from bravado.client import SwaggerClient
from bravado.requests_client import RequestsClient, Authenticator
from esi import app_settings
from esi.errors import TokenExpiredError
try:
    import urlparse
except ImportError: #py3
    from urllib import parse as urlparse


class TokenAuthenticator(Authenticator):
    """
    Adds the authorization header containing access token, if specified.
    Sets ESI datasource to tranquility or singularity.
    """
    def __init__(self, token=None, datasource=None):
        self.token = token
        self.datasource = datasource
        self.host = urlparse.urlsplit(app_settings.ESI_API_URL).hostname

    def apply(self, request):
        if self.token and self.token.expired:
            if self.token.can_refresh:
                self.token.refresh()
            else:
                raise TokenExpiredError()
        request.headers['Authorization'] = 'Bearer ' + self.token.access_token if self.token else None
        request.params['datasource'] = self.datasource or app_settings.ESI_API_DATASOURCE
        return request


def esi_client_factory(token=None, datasource=None):
    """
    Generates an ESI client.
    :param token: :class:`esi.Token` used to access authenticated endpoints.
    :param datasource: Name of the ESI datasource to access.
    :return: :class:`bravado.client.SwaggerClient`
    """
    if token or datasource:
        requests_client = RequestsClient()
        requests_client.authenticator = TokenAuthenticator(token=token, datasource=datasource)
    else:
        requests_client = None
    return SwaggerClient.from_url(app_settings.ESI_SWAGGER_URL, http_client=requests_client)
