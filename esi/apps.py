from __future__ import unicode_literals

from django.apps import AppConfig


class EsiConfig(AppConfig):
    name = 'esi'
    verbose_name = 'EVE Swagger Interface'

    def ready(self):
        super(EsiConfig, self).ready()
        from esi import checks