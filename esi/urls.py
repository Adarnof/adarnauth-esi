from __future__ import unicode_literals
from django.conf.urls import url
import esi.views

app_name = 'esi'
urlpatterns = [
    url(r'^callback/$', esi.views.receive_callback, name='callback'),
]
