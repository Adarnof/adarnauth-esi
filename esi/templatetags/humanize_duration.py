from django import template
from math import floor
from django.utils.translation import gettext_lazy as _

register = template.Library()


@register.filter
def format_seconds(s):
    hours = floor(s / 3600)
    mins = floor(s - (hours * 3600) / 60)
    secs = floor(s - (mins * 60))

    if hours:
        out = str(hours)
        if mins:
            out = "{}.{:01.0f}".format(hours, mins)
        word = _('hours') if hours or mins else _('hour')
    elif mins:
        out = mins
        if secs:
            out = "{}.{:01.0f}".format(mins, secs)
        word = _('minutes') if mins or secs else _('minute')
    else:
        out = secs
        word = _('seconds') if out > 1 else _('second')
    return "{} {}".format(out, word)
