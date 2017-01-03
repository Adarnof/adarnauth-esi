from __future__ import unicode_literals
from django.db import models
from requests_oauthlib import OAuth2Session
from esi import app_settings
import requests
from django.utils import timezone
from datetime import timedelta
from django.utils.six import string_types
from esi.errors import TokenError


def _process_scopes(scopes):
    # support space-delimited string scopes or lists
    if isinstance(scopes, string_types):
        scopes = scopes.split()
    return scopes


class TokenQueryset(models.QuerySet):
    def get_expired(self):
        """
        Get all tokens which have expired.
        :return: All expired tokens.
        :rtype: :class:`esi.managers.TokenQueryset`
        """
        max_age = timezone.now() - timedelta(seconds=app_settings.ESI_TOKEN_VALID_DURATION)
        return self.filter(created__lte=max_age)

    def bulk_refresh(self):
        """
        Refreshes all refreshable tokens in the queryset.
        Deletes any tokens which fail to refresh.
        Deletes any tokens which are expired and cannot refresh.
        """
        session = OAuth2Session(app_settings.ESI_SSO_CLIENT_ID)
        auth = requests.auth.HTTPBasicAuth(app_settings.ESI_SSO_CLIENT_ID, app_settings.ESI_SSO_CLIENT_SECRET)
        for model in self.filter(refresh_token__isnull=False):
            try:
                model.refresh(session=session, auth=auth)
            except TokenError:
                model.delete()
        self.filter(refresh_token__isnull=True).get_expired().delete()

    def require_valid(self):
        """
        Ensures all tokens are still valid. If expired, attempts to refresh.
        Deletes those which fail to refresh or cannot be refreshed.
        :return: All tokens which are still valid.
        :rtype: :class:`esi.managers.TokenQueryset`
        """
        self.get_expired().bulk_refresh()
        return self.filter(pk__isnull=False)

    def require_scopes(self, scope_string):
        """
        :param scope_string: The required scopes.
        :type scope_string: Union[str, list]
        :return: The tokens with all requested scopes.
        :rtype: :class:`esi.managers.TokenQueryset`
        """
        scopes = _process_scopes(scope_string)
        for s in scopes:
            self = self.filter(scopes__name=str(s))
        return self


class TokenManager(models.Manager):
    def get_queryset(self):
        """
        Replace base queryset model with custom TokenQueryset
        :rtype: :class:`esi.managers.TokenQueryset`
        """
        return TokenQueryset(self.model, using=self._db)

    def create_from_request(self, request):
        oauth = OAuth2Session(app_settings.ESI_SSO_CLIENT_ID, redirect_uri=app_settings.ESI_SSO_CALLBACK_URL)
        token = oauth.fetch_token(app_settings.ESI_TOKEN_URL, client_secret=app_settings.ESI_SSO_CLIENT_SECRET,
                                  code=request.GET.get('code'))

        token_data = oauth.request('get', app_settings.ESI_TOKEN_VERIFY_URL).json()

        model = self.create(
            character_id=token_data['CharacterID'],
            character_name=token_data['CharacterName'],
            character_owner_hash=token_data['CharacterOwnerHash'],
            access_token=token['access_token'],
            refresh_token=token['refresh_token'],
            token_type=token_data['TokenType'],
            user=request.user if request.user.is_authenticated else None
        )

        if 'Scopes' in token_data:
            from esi.models import Scope
            for s in token_data['Scopes'].split():
                try:
                    scope = Scope.objects.get(name=s)
                    model.scopes.add(scope)
                except Scope.DoesNotExist:
                    # This scope isn't included in a data migration. Create a placeholder until it updates.
                    try:
                        help_text = s.split('.')[1].replace('_', ' ').capitalize()
                    except IndexError:
                        # Unusual scope name, missing periods.
                        help_text = s.replace('_', ' ').capitalize()
                    scope = Scope.objects.create(name=s, help_text=help_text)
                    model.scopes.add(scope)

        return model
