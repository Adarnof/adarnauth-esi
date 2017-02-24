from __future__ import unicode_literals
from bravado.client import SwaggerClient, CONFIG_DEFAULTS
from bravado.requests_client import RequestsClient, Authenticator
from bravado.swagger_model import Loader
from bravado_core.spec import Spec
from esi import app_settings
from esi.errors import TokenExpiredError
from django.core.cache import cache

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


def build_cache_name(name):
    """
    Cache key name formatter
    :param name: Name of the spec dict to cache, usually version
    :return: String name for cache key
    :rtype: str
    """
    return 'esi_swaggerspec_%s' % name


def cache_spec(name, spec):
    """
    Cache the spec dict
    :param name: Version name
    :param spec: Spec dict
    :return: True if cached
    """
    return cache.set(build_cache_name(name), spec, app_settings.ESI_SPEC_CACHE_DURATION)


def build_spec_url(spec_version):
    """
    Generates the URL to swagger.json for the ESI version
    :param spec_version: Name of the swagger spec version, like latest or v4
    :return: URL to swagger.json for the requested spec version
    """
    return urlparse.urljoin(app_settings.ESI_API_URL, spec_version + '/swagger.json')


def get_spec(name, http_client=None, config=None):
    """
    :param name: Name of the revision of spec, eg latest or v4
    :param http_client: Requests client used for retrieving specs
    :param config: Spec configuration - see Spec.CONFIG_DEFAULTS
    :return: :class:`bravado_core.spec.Spec`
    """

    def load_spec():
        loader_http_client = http_client or RequestsClient()
        loader = Loader(loader_http_client)
        return loader.load_spec(build_spec_url(name))

    spec_dict = cache.get_or_set(build_cache_name(name), load_spec, app_settings.ESI_SPEC_CACHE_DURATION)
    config = dict(CONFIG_DEFAULTS, **(config or {}))
    return Spec.from_dict(spec_dict, build_spec_url(name), http_client, config)


def build_spec(base_version, http_client=None, **kwargs):
    """
    Generates the Spec used to initialize a SwaggerClient, supporting mixed resource versions
    :param http_client: :class:`bravado.requests_client.RequestsClient`
    :param base_version: Version to base the spec on. Any resource without an explicit version will be this.
    :param kwargs: Explicit resource versions, by name (eg Character='v4')
    :return: :class:`bravado_core.spec.Spec`
    """
    base_spec = get_spec(base_version, http_client=http_client)
    if kwargs:
        for resource, resource_version in kwargs.items():
            versioned_spec = get_spec(resource_version, http_client=http_client)
            try:
                spec_resource = versioned_spec.resources[resource.capitalize()]
            except KeyError:
                raise AttributeError(
                    'Resource {0} not found on API revision {1}'.format(resource, resource_version))
            base_spec.resources[resource.capitalize()] = spec_resource
    return base_spec


def esi_client_factory(token=None, datasource=None, version=None, **kwargs):
    """
    Generates an ESI client.
    :param token: :class:`esi.Token` used to access authenticated endpoints.
    :param datasource: Name of the ESI datasource to access.
    :param version: Base ESI API version. Accepted values are 'legacy', 'latest', 'dev', or 'vX' where X is a number
    :param kwargs: Explicit resource versions to build, in the form Character='v4'. Same values accepted as version.
    :return: :class:`bravado.client.SwaggerClient`
    """
    if token or datasource:
        requests_client = RequestsClient()
        requests_client.authenticator = TokenAuthenticator(token=token, datasource=datasource)
    else:
        requests_client = None

    api_version = version or app_settings.ESI_API_VERSION

    spec = build_spec(api_version, http_client=requests_client, **kwargs)
    return SwaggerClient(spec)
