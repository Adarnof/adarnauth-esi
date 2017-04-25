from __future__ import unicode_literals
from django.utils import timezone
from datetime import timedelta
from esi.models import CallbackRedirect, Token


def cleanup_callbackredirect(max_age=300):
    """
    Delete old :model:`esi.CallbackRedirect` models.
    Accepts a max_age parameter, in seconds (default 300).
    """
    max_age = timezone.now() - timedelta(seconds=max_age)
    CallbackRedirect.objects.filter(created__lte=max_age).delete()


def cleanup_token():
    """
    Delete expired :model:`esi.Token` models.
    """
    Token.objects.all().get_expired().bulk_refresh()
