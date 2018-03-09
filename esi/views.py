from __future__ import unicode_literals

from django.shortcuts import redirect, get_object_or_404, render
from django.utils.six import string_types
from django.urls import reverse
from esi.models import CallbackRedirect, Token
from esi import app_settings
from esi.decorators import tokens_required
from django.http.response import HttpResponseBadRequest
from requests_oauthlib import OAuth2Session
import logging

logger = logging.getLogger(__name__)


def sso_redirect(request, scopes=list([]), return_to=None):
    """
    Generates a :model:`esi.CallbackRedirect` for the specified request.
    Redirects to EVE for login.
    Accepts a view or URL name as a redirect after SSO.
    """
    logger.debug("Initiating redirect of {0} session {1}".format(request.user, request.session.session_key[:5]))
    if isinstance(scopes, string_types):
        scopes = list([scopes])

    # ensure only one callback redirect model per session
    CallbackRedirect.objects.filter(session_key=request.session.session_key).delete()

    # ensure session installed in database
    if not request.session.exists(request.session.session_key):
        logger.debug("Creating new session before redirect.")
        request.session.create()

    if return_to:
        url = reverse(return_to)
    else:
        url = request.get_full_path()

    oauth = OAuth2Session(app_settings.ESI_SSO_CLIENT_ID, redirect_uri=app_settings.ESI_SSO_CALLBACK_URL, scope=scopes)
    redirect_url, state = oauth.authorization_url(app_settings.ESI_OAUTH_LOGIN_URL)

    CallbackRedirect.objects.create(session_key=request.session.session_key, state=state, url=url)
    logger.debug("Redirecting {0} session {1} to SSO. Callback will be redirected to {2}".format(request.user, request.session.session_key[:5], url))
    return redirect(redirect_url)


def receive_callback(request):
    """
    Parses SSO callback, validates, retrieves :model:`esi.Token`, and internally redirects to the target url.
    """
    logger.debug("Received callback for {0} session {1}".format(request.user, request.session.session_key[:5]))
    # make sure request has required parameters
    code = request.GET.get('code', None)
    state = request.GET.get('state', None)
    try:
        assert code
        assert state
    except AssertionError:
        logger.debug("Missing parameters for code exchange.")
        return HttpResponseBadRequest()

    callback = get_object_or_404(CallbackRedirect, state=state, session_key=request.session.session_key)
    token = Token.objects.create_from_request(request)
    callback.token = token
    callback.save()
    logger.debug(
        "Processed callback for {0} session {1}. Redirecting to {2}".format(request.user, request.session.session_key[:5], callback.url))
    return redirect(callback.url)


def select_token(request, scopes='', new=False):
    """
    Presents the user with a selection of applicable tokens for the requested view.
    """

    @tokens_required(scopes=scopes, new=new)
    def _token_list(r, tokens):
        context = {
            'tokens': tokens,
            'base_template': app_settings.ESI_BASE_TEMPLATE,
        }
        return render(r, 'esi/select_token.html', context=context)

    return _token_list(request)
