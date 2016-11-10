from __future__ import unicode_literals
from celery.task import periodic_task
from django.utils import timezone
from datetime import timedelta
from esi.models import CallbackRedirect, Token
from esi.errors import TokenError


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
    for model in Token.objects.all():
        if model.expired:
            if model.can_refresh:
                try:
                    model.refresh()
                except TokenError:
                    model.delete()
            else:
                model.delete()
