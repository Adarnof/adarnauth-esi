from __future__ import unicode_literals
from bravado.client import SwaggerClient as BaseClient, CONFIG_DEFAULTS, inject_headers_for_remote_refs
from bravado import requests_client
from bravado.http_future import HttpFuture
from esi.errors import TokenExpiredError
from esi import app_settings
from django.core.cache import cache
from datetime import datetime
from hashlib import md5
import json
from contextlib import contextmanager

try:
    import urlparse
except ImportError:  # py3
    from urllib import parse as urlparse


class CachingHttpFuture(HttpFuture):
    """
    Used to add caching to certain HTTP requests according to "Expires" header
    """

    def __init__(self, *args, **kwargs):
        super(CachingHttpFuture, self).__init__(*args, **kwargs)
        self.cache_key = self._build_cache_key(self.future.request)

    @staticmethod
    def _build_cache_key(request):
        """
        Generated the key name used to cache responses
        :param request: request used to retrieve API response
        :return: formatted cache name
        """
        str_hash = md5(
            (request.method + request.url + str(request.params) + str(request.data) + str(request.json)).encode(
                'utf-8')).hexdigest()
        return 'esi_%s' % str_hash

    @staticmethod
    def _time_to_expiry(expires):
        """
        Determines the seconds until a HTTP header "Expires" timestamp
        :param expires: HTTP response "Expires" header
        :return: seconds until "Expires" time
        """
        try:
            expires_dt = datetime.strptime(str(expires), '%a, %d %b %Y %H:%M:%S %Z')
            delta = expires_dt - datetime.utcnow()
            return delta.seconds
        except ValueError:
            return 0

    def result(self, **kwargs):
        if app_settings.ESI_CACHE_RESPONSE and self.future.request.method == 'GET' and self.operation is not None:
            """
            Only cache if all are true:
             - settings dictate caching
             - it's a http get request
             - it's to a swagger api endpoint
            """
            cached = cache.get(self.cache_key)
            if cached:
                result, response = cached
            else:
                _also_return_response = self.also_return_response  # preserve original value
                self.also_return_response = True  # override to always get the raw response for expiry header
                result, response = super(CachingHttpFuture, self).result(**kwargs)
                self.also_return_response = _also_return_response  # restore original value

                if 'Expires' in response.headers:
                    expires = self._time_to_expiry(response.headers['Expires'])
                    if expires > 0:
                        cache.set(self.cache_key, (result, response), expires)

            if self.also_return_response:
                return result, response
            else:
                return result
        else:
            return super(CachingHttpFuture, self).result(**kwargs)


requests_client.HttpFuture = CachingHttpFuture


class TokenAuthenticator(requests_client.Authenticator):
    """
    Adds the authorization header containing access token, if specified.
    Sets ESI datasource to tranquility or singularity.
    """

    def __init__(self, token):
        host = urlparse.urlsplit(app_settings.ESI_API_URL).hostname
        super(TokenAuthenticator, self).__init__(host)
        self.token = token

    def apply(self, request):
        # ensure token is still valid
        if self.token and self.token.expired:
            if self.token.can_refresh:
                self.token.refresh()
            else:
                raise TokenExpiredError()

        # inject header containing OAuth token
        request.headers['Authorization'] = 'Bearer ' + self.token.access_token
        return request


class SwaggerClient(BaseClient):
    """
    Extends the bravado SwaggerClient to allow reading spec from file.
    Provides a contextmanager for authenticating clients temporarily.
    """

    @classmethod
    def from_file(cls, path, http_client=None, request_headers=None, config=None):
        http_client = http_client or requests_client.RequestsClient()

        # SwaggerClient.from_url does this so I will too
        if request_headers:
            http_client.request = inject_headers_for_remote_refs(http_client.request, request_headers)

        # read the file and get json dictionary of contents
        with open(path, 'r') as f:
            spec_dict = json.loads(f.read())

        # caching does not allow returning models, so ensure they're not used here
        config = config.update({'use_models': False})

        return cls.from_spec(spec_dict, http_client=http_client, config=config)

    @contextmanager
    def authenticate(self, token):
        # swap authenticator for TokenAuthenticator, but keep it
        old_authenticator, self.swagger_spec.http_client.authenticator = \
            self.swagger_spec.http_client.authenticator, TokenAuthenticator(token)

        # return the client for use
        yield self

        # put the old authenticator back
        self.swagger_spec.http_client.authenticator = old_authenticator


def minimize_spec(spec_dict, operations=None, resources=None):
    """
    Trims down a source spec dict to only the operations or resources indicated.
    :param spec_dict: The source spec dict to minimize.
    :type spec_dict: dict
    :param operations: A list of operation names to retain.
    :type operations: list of str
    :param resources: A list of resource names to retain.
    :type resources: list of str
    :return: Minimized swagger spec dict
    :rtype: dict
    """
    operations = operations or []
    resources = resources or []

    # keep the ugly overhead for now but only add paths we need
    minimized = {key: value for key, value in spec_dict.items() if key != 'paths'}
    minimized['paths'] = {}

    for path_name, path in spec_dict['paths'].items():
        for method, data in path.items():
            if data['operationId'] in operations or any(tag in resources for tag in data['tags']):
                if path_name not in minimized['paths']:
                    minimized['paths'][path_name] = {}
                minimized['paths'][path_name][method] = data

    return minimized
