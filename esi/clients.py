from __future__ import unicode_literals
from bravado.client import SwaggerClient
from bravado.requests_client import RequestsClient
from esi import app_settings
from esi.errors import TokenExpiredError
from requests.auth import AuthBase


class TokenAuthentication(AuthBase):
    def __init__(self, token):
        self.token = token

    def __call__(self, r):
        if self.token.expired:
            if self.token.can_refresh:
                self.token.refresh()
            else:
                raise TokenExpiredError()
        r.headers['Authorization'] = 'Bearer ' + self.token.access_token
        return r


def esi_client_factory(token=None):
    if token:
        requests_client = RequestsClient()
        requests_client.authenticator = TokenAuthentication(token)
    else:
        requests_client = None
    return SwaggerClient.from_url(app_settings.ESI_SWAGGER_URL, http_client=requests_client)
