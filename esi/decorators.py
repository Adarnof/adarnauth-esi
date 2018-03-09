from __future__ import unicode_literals
from functools import wraps
from django.utils.decorators import available_attrs
from esi.models import Token, CallbackRedirect
import logging

logger = logging.getLogger(__name__)


def _check_callback(request):
    # ensure session installed in database
    if not request.session.exists(request.session.session_key):
        logger.debug("Creating new session for {0}".format(request.user))
        request.session.create()

    # clean up callback redirect, pass token if new requested
    try:
        model = CallbackRedirect.objects.get(session_key=request.session.session_key)
        token = Token.objects.get(pk=model.token.pk)
        model.delete()
        logger.debug(
            "Retrieved new token from callback for {0} session {1}".format(request.user, request.session.session_key[:5]))
        return token
    except (CallbackRedirect.DoesNotExist, Token.DoesNotExist, AttributeError):
        logger.debug("No callback for {0} session {1}".format(request.user, request.session.session_key[:5]))
        return None


def tokens_required(scopes='', new=False):
    """
    Decorator for views to request an ESI Token.
    Accepts required scopes as a space-delimited string
    or list of strings of scope names.
    Can require a new token to be retrieved by SSO.
    Returns a QueryDict of Tokens.
    """

    def decorator(view_func):
        @wraps(view_func, assigned=available_attrs(view_func))
        def _wrapped_view(request, *args, **kwargs):

            # if we're coming back from SSO for a new token, return it
            token = _check_callback(request)
            if token and new:
                tokens = Token.objects.filter(pk=token.pk)
                logger.debug("Returning new token.")
                return view_func(request, tokens, *args, **kwargs)

            if not new:
                # ensure user logged in to check existing tokens
                if not request.user.is_authenticated:
                    logger.debug(
                        "Session {0} is not logged in. Redirecting to login.".format(request.session.session_key[:5]))
                    from django.contrib.auth.views import redirect_to_login
                    return redirect_to_login(request.get_full_path())

                # collect tokens in db, check if still valid, return if any
                tokens = Token.objects.filter(user__pk=request.user.pk).require_scopes(scopes).require_valid()
                if tokens.exists():
                    logger.debug("Retrieved {0} tokens for {1} session {2}".format(tokens.count(), request.user,
                                                                                   request.session.session_key[:5]))
                    return view_func(request, tokens, *args, **kwargs)

            # trigger creation of new token via sso
            logger.debug("No tokens identified for {0} session {1}. Redirecting to SSO.".format(request.user, request.session.session_key[:5]))
            from esi.views import sso_redirect
            return sso_redirect(request, scopes=scopes)

        return _wrapped_view

    return decorator


def token_required(scopes='', new=False):
    """
    Decorator for views which supplies a single, user-selected token for the view to process.
    Same parameters as tokens_required.
    """

    def decorator(view_func):
        @wraps(view_func, assigned=available_attrs(view_func))
        def _wrapped_view(request, *args, **kwargs):

            # if we're coming back from SSO for a new token, return it
            token = _check_callback(request)
            if token and new:
                logger.debug("Got new token from {0} session {1}. Returning to view.".format(request.user, request.session.session_key[:5]))
                return view_func(request, token, *args, **kwargs)

            # if we're selecting a token, return it
            if request.method == 'POST':
                if request.POST.get("_add", False):
                    logger.debug("{0} has selected to add new token. Redirecting to SSO.".format(request.user))
                    # user has selected to add a new token
                    from esi.views import sso_redirect
                    return sso_redirect(request, scopes=scopes)

                token_pk = request.POST.get('_token', None)
                if token_pk:
                    logger.debug("{0} has selected token {1}".format(request.user, token_pk))
                    try:
                        token = Token.objects.get(pk=token_pk)
                        # ensure token belongs to this user and has required scopes
                        if ((token.user and token.user == request.user) or not token.user) and Token.objects.filter(
                                pk=token_pk).require_scopes(scopes).require_valid().exists():
                            logger.debug("Selected token fulfills requirements of view. Returning.")
                            return view_func(request, token, *args, **kwargs)
                    except Token.DoesNotExist:
                        logger.debug("Token {0} not found.".format(token_pk))
                        pass

            if not new:
                # present the user with token choices
                tokens = Token.objects.filter(user__pk=request.user.pk).require_scopes(scopes).require_valid()
                if tokens.exists():
                    logger.debug("Returning list of available tokens for {0}.".format(request.user))
                    from esi.views import select_token
                    return select_token(request, scopes=scopes, new=new)
                else:
                    logger.debug("No tokens found for {0} session {1} with scopes {2}".format(request.user, request.session.session_key[:5], scopes))

            # prompt the user to add a new token
            logger.debug("Redirecting {0} session {1} to SSO.".format(request.user, request.session.session_key[:5]))
            from esi.views import sso_redirect
            return sso_redirect(request, scopes=scopes)

        return _wrapped_view

    return decorator
