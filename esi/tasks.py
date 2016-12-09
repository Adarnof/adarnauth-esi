from __future__ import unicode_literals
from celery.task import periodic_task
from django.utils import timezone
from datetime import timedelta
from requests_oauthlib import OAuth2Session
import requests
from esi.models import CallbackRedirect, Token
from esi.errors import TokenError
from esi import app_settings


@periodic_task(run_every=timedelta(hours=4))
def cleanup_callbackredirect(max_age=300):
    """
    Delete old :model:`esi.CallbackRedirect` models.
    Accepts a max_age parameter, in seconds (default 300).
    """
    max_age_obj = timedelta(seconds=max_age)
    CallbackRedirect.objects.filter(created__lte=timezone.now() - max_age_obj).delete()


@periodic_task(run_every=timedelta(days=1))
def cleanup_token():
    """
    Delete expired :model:`esi.Token` models.
    """
    session = OAuth2Session(app_settings.ESI_SSO_CLIENT_ID)
    auth = requests.auth.HTTPBasicAuth(app_settings.ESI_SSO_CLIENT_ID, app_settings.ESI_SSO_CLIENT_SECRET)
    max_age = timezone.now() - timedelta(seconds=app_settings.ESI_TOKEN_VALID_DURATION)
    tokens = Token.objects.filter(created__lte=max_age)
    for model in tokens.filter(refresh_token__isnull=False):
        try:
            model.refresh(session=session, auth=auth)
        except TokenError:
            model.delete()
    tokens.filter(refresh_token__isnull=True).delete()
