from __future__ import unicode_literals
from bravado.client import SwaggerClient
from bravado.requests_client import RequestsClient, Authenticator
from esi import app_settings
from esi.errors import TokenExpiredError
try:
    import urlparse
except ImportError:  # py3
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


def esi_client_factory(token=None, datasource=None, version=None):
    """
    Generates an ESI client.
    :param token: :class:`esi.Token` used to access authenticated endpoints.
    :param datasource: Name of the ESI datasource to access.
    :param version: ESI API version. Accepted values are 'legacy', 'latest', 'dev', or 'vX' where X is a numeric version
    :return: :class:`bravado.client.SwaggerClient`
    """
    if token or datasource:
        requests_client = RequestsClient()
        requests_client.authenticator = TokenAuthenticator(token=token, datasource=datasource)
    else:
        requests_client = None

    api_version = version or app_settings.ESI_API_VERSION
    url = urlparse.urljoin(app_settings.ESI_API_URL, api_version + '/swagger.json')
    return SwaggerClient.from_url(url, http_client=requests_client)
