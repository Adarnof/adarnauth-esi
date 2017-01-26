from __future__ import unicode_literals

default_app_config = 'esi.apps.EsiConfig'

import pkg_resources
try:
    __version__ = pkg_resources.get_distribution("adarnauth-esi").version
except pkg_resources.DistributionNotFound:
    __version__ = 'unknown'

