from __future__ import unicode_literals
from django.utils import timezone
from datetime import timedelta
from esi.models import CallbackRedirect, Token
from celery import shared_task
import logging


logger = logging.getLogger(__name__)


@shared_task
def cleanup_callbackredirect(max_age=300):
    """
    Delete old :model:`esi.CallbackRedirect` models.
    Accepts a max_age parameter, in seconds (default 300).
    """
    max_age = timezone.now() - timedelta(seconds=max_age)
    logger.debug("Deleting all callback redirects created before {0}".format(max_age.strftime("%b %d %Y %H:%M:%S")))
    CallbackRedirect.objects.filter(created__lte=max_age).delete()


@shared_task
def cleanup_token():
    """
    Delete expired :model:`esi.Token` models.
    """
    logger.debug("Triggering bulk refresh of all expired tokens.")
    Token.objects.all().get_expired().bulk_refresh()
