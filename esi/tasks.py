from __future__ import unicode_literals
from celery.task import periodic_task
from django.utils import timezone
from datetime import timedelta
from esi.models import CallbackRedirect, Token


@periodic_task(run_every=timedelta(hours=4))
def cleanup_callbackredirect(max_age=300):
    """
    Delete old :model:`esi.CallbackRedirect` models.
    Accepts a max_age parameter, in seconds (default 300).
    """
    max_age = timezone.now() - timedelta(seconds=max_age)
    CallbackRedirect.objects.filter(created__lte=max_age).delete()


@periodic_task(run_every=timedelta(days=1))
def cleanup_token():
    """
    Delete expired :model:`esi.Token` models.
    """
    Token.objects.get_expired().bulk_refresh()
