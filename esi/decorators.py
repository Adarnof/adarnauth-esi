from __future__ import unicode_literals
from functools import wraps
from django.utils.decorators import available_attrs
from esi.models import Token, CallbackRedirect


def _check_callback(request):
    # ensure session installed in database
    if not request.session.exists(request.session.session_key):
        request.session.create()

    # clean up callback redirect, pass token if new requested
    try:
        model = CallbackRedirect.objects.get(session_key=request.session.session_key)
        token = Token.objects.get(pk=model.token.pk)
        model.delete()
        return token
    except (CallbackRedirect.DoesNotExist, Token.DoesNotExist, AttributeError):
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
                return view_func(request, tokens, *args, **kwargs)

            if not new:
                # ensure user logged in to check existing tokens
                if not request.user.is_authenticated:
                    from django.contrib.auth.views import redirect_to_login
                    return redirect_to_login(request.get_full_path())

                # collect tokens in db, check if still valid, return if any
                tokens = Token.objects.filter(user__pk=request.user.pk).require_scopes(scopes).require_valid()
                if tokens.exists():
                    return view_func(request, tokens, *args, **kwargs)

            # trigger creation of new token via sso
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
                return view_func(request, token, *args, **kwargs)

            # if we're selecting a token, return it
            if request.method == 'POST':
                if request.POST.get("_add", False):
                    # user has selected to add a new token
                    from esi.views import sso_redirect
                    return sso_redirect(request, scopes=scopes)

                token_pk = request.POST.get('_token', None)
                if token_pk:
                    try:
                        token = Token.objects.get(pk=token_pk)
                        # ensure token belongs to this user and has required scopes
                        if ((token.user and token.user == request.user) or not token.user) and Token.objects.filter(
                                pk=token_pk).require_scopes(scopes).require_valid().exists():
                            return view_func(request, token, *args, **kwargs)
                    except Token.DoesNotExist:
                        pass

            # present the user with token choices
            tokens = Token.objects.filter(user__pk=request.user.pk).require_scopes(scopes).require_valid()
            if tokens.exists():
                from esi.views import select_token
                return select_token(request, scopes=scopes, new=new)
            else:
                # no tokens are available, so prompt the user to add one
                from esi.views import sso_redirect
                return sso_redirect(request, scopes=scopes)

        return _wrapped_view

    return decorator
