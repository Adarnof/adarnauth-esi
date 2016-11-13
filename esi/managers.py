from __future__ import unicode_literals
from django.db import models
from requests_oauthlib import OAuth2Session
from esi import app_settings


class TokenManager(models.Manager):
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

        if 'Scopes' in token:
            from esi.models import Scope
            for s in token['Scopes'].split():
                scope = Scope.objects.get_or_create(name=s)[0]
                model.scopes.add(scope)

        return model
