from __future__ import unicode_literals

from django.shortcuts import redirect, render
from django.utils.six import string_types
from django.urls import reverse
from esi.models import Token
from esi import app_settings
from esi.decorators import tokens_required
from django.http.response import HttpResponseBadRequest
from requests_oauthlib import OAuth2Session
from django.core.cache import cache
from hashlib import md5


def _cache_key_name(request, state):
    return 'esi_redirect_{}'.format(md5(request.session.session_key + state).hexdigest())


def sso_redirect(request, scopes=list([]), return_to=None):
    """
    Generates a :model:`esi.CallbackRedirect` for the specified request.
    Redirects to EVE for login.
    Accepts a view or URL name as a redirect after SSO.
    """
    if isinstance(scopes, string_types):
        scopes = list([scopes])

    # ensure session installed in database
    if not request.session.exists(request.session.session_key):
        request.session.create()

    if return_to:
        url = reverse(return_to)
    else:
        url = request.get_full_path()

    oauth = OAuth2Session(app_settings.CLIENT_ID, redirect_uri=app_settings.CALLBACK_URL, scope=scopes)
    redirect_url, state = oauth.authorization_url(app_settings.OAUTH_LOGIN_URL)

    cache.set(_cache_key_name(request, state), url, app_settings.CALLBACK_TIMEOUT)

    return redirect(redirect_url)


def receive_callback(request):
    """
    Parses SSO callback, validates, retrieves :model:`esi.Token`, and internally redirects to the target url.
    """
    # make sure request has required parameters
    code = request.GET.get('code', None)
    state = request.GET.get('state', None)
    try:
        assert code
        assert state
    except AssertionError:
        return HttpResponseBadRequest()

    url = cache.get(_cache_key_name(request, state))

    if not url:
        return render(request, 'esi/callback_not_found.html')

    token = Token.objects.create_from_request(request)
    request.session['_esi_token'] = token
    return redirect(url)


def select_token(request, scopes='', new=False):
    """
    Presents the user with a selection of applicable tokens for the requested view.
    """

    @tokens_required(scopes=scopes, new=new)
    def _token_list(r, tokens):
        context = {
            'tokens': tokens,
            'base_template': app_settings.BASE_TEMPLATE,
        }
        return render(r, 'esi/select_token.html', context=context)

    return _token_list(request)
