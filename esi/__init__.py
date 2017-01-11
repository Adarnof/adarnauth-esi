from __future__ import unicode_literals

default_app_config = 'esi.apps.EsiConfig'

import pkg_resources
__version__ = pkg_resources.require("adarnauth-esi")[0].version

