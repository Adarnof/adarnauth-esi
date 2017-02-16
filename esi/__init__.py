from __future__ import unicode_literals
import pkg_resources

default_app_config = 'esi.apps.EsiConfig'

try:
    __version__ = pkg_resources.get_distribution("adarnauth-esi").version
except pkg_resources.DistributionNotFound:
    __version__ = 'unknown'

