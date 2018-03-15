from django.db import models
from esi import app_settings
from django.conf import settings
from requests.auth import HTTPBasicAuth
from requests_oauthlib import OAuth2Session
from .managers import TokenManager
from .errors import TokenInvalidError, NotRefreshableTokenError, TokenExpiredError
from oauthlib.oauth2.rfc6749.errors import InvalidGrantError, MissingTokenError, InvalidClientError, InvalidTokenError
from django.core.exceptions import ImproperlyConfigured
import re
from django.core.cache import cache
from hashlib import md5
from .app_settings import TOKEN_VALID_DURATION
from django.utils import timezone
from datetime import timedelta


class Scope(models.Model):
    """
    Represents an access scope granted by SSO.
    """
    name = models.CharField(max_length=100, unique=True, help_text="The official CCP name for the scope.", db_index=True)
    description = models.TextField(help_text="The description of the scope.")

    @property
    def friendly_name(self):
        try:
            return re.sub('_', ' ', self.name.split('.')[1]).strip()
        except IndexError:
            out = re.sub(r'([A-Z])', r' \1', str(self.name))
            return out.capitalize()

    def __str__(self):
        return self.name


class Token(models.Model):
    """
    EVE Swagger Interface Access Token

    Contains information about the authenticating character and scopes granted to this token.
    Contains the access token required for ESI authentication as well as refreshing.
    """

    refresh_token = models.CharField(max_length=254, blank=True, null=True,
                                     help_text="A re-usable token to generate new access tokens upon expiry.",
                                     editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, blank=True, null=True,
                             help_text="The user to whom this token belongs.")
    character_id = models.IntegerField(help_text="The ID of the EVE character who authenticated by SSO.", db_index=True)
    character_name = models.CharField(max_length=100,
                                      help_text="The name of the EVE character who authenticated by SSO.")
    token_type = models.CharField(max_length=100, choices=(('Character', 'Character'), ('Corporation', 'Corporation'),),
                                  default='Character', help_text="The applicable range of the token.")
    character_owner_hash = models.CharField(max_length=254,
                                            help_text="The unique string identifying this character and its owning EVE "
                                                      "account. Changes if the owning account changes.")
    scopes = models.ManyToManyField(Scope, blank=True, help_text="The access scopes granted by this token.")
    datasource = models.CharField(max_length=11, default=app_settings.API_DATASOURCE, editable=False, db_index=True)
    created = models.DateTimeField(auto_now=True, editable=False)
    updated = models.DateTimeField(auto_now_add=True, editable=False)

    objects = TokenManager()

    def __str__(self):
        return "%s - %s" % (self.character_name, ", ".join(sorted(s.name for s in self.scopes.all())))

    def __repr__(self):
        return "<{}(id={}): {}, {}>".format(
            self.__class__.__name__,
            self.pk,
            self.character_id,
            self.character_name,
        )

    @property
    def expired(self):
        """
        Determins if this token has expired.

        :return: True if expired
        """
        return self.updated + timedelta(seconds=TOKEN_VALID_DURATION) < timezone.now()

    @property
    def can_refresh(self):
        """
        Determines if this token can be refreshed upon expiry

        :return: True if can be refreshed
        """
        return bool(self.refresh_token)

    def refresh(self, session=None, auth=None):
        """
        Refreshes the token.

        :param session: :class:`requests_oauthlib.OAuth2Session`
        :param auth: :class:`requests.auth.HTTPBasicAuth`
        """
        if self.can_refresh:
            if not session:
                session = OAuth2Session(app_settings.CLIENT_ID)
            if not auth:
                auth = HTTPBasicAuth(app_settings.CLIENT_ID, app_settings.CLIENT_SECRET)
            try:
                token = session.refresh_token(app_settings.TOKEN_URL, refresh_token=self.refresh_token, auth=auth)
                self.access_token = token['access_token']
                self.refresh_token = token['refresh_token']
                self.save()
            except (InvalidGrantError, MissingTokenError, InvalidTokenError):
                raise TokenInvalidError()
            except InvalidClientError:
                raise ImproperlyConfigured('Verify ESI_SSO_CLIENT_ID and ESI_SSO_CLIENT_SECRET settings.')
        else:
            raise NotRefreshableTokenError()

    @classmethod
    def get_token_data(cls, access_token):
        """
        Gets the character and scopes of a given access token

        :param access_token: access token used in Authorization request header
        :return: dictionary of token data
        {
            "CharacterID": 234899860,
            "CharacterName": "Adarnof",
            "ExpiresOn": "2018-04-17T10:17:02.254876Z",
            "Scopes": "esi-location.read_location.v1 esi-location.read_ship_type.v1",
            "TokenType": "Character",
            "CharacterOwnerHash": "HKvB...r=3E"
        }
        """
        session = OAuth2Session(app_settings.CLIENT_ID, token={'access_token': access_token})
        return session.request('get', app_settings.TOKEN_VERIFY_URL).json()

    def update_token_data(self, commit=True):
        """
        Updates character-related fields of the token.

        :param commit: True to save the model after updating
        """
        token_data = self.get_token_data(self.access_token)
        self.character_id = token_data['CharacterID']
        self.character_name = token_data['CharacterName']
        self.character_owner_hash = token_data['CharacterOwnerHash']
        self.token_type = token_data['TokenType']
        if commit:
            self.save()

    def _token_cache_key_name(self):
        """
        Generates a cache key name for the token

        :return: String cache key name unique to the token
        """
        return 'esi_token_{}'.format(md5(self.pk + self.refresh_token).hexdigest())

    @property
    def access_token(self):
        """
        The access token required for Authorization request headers. Refreshes if expired.

        :return: String access token
        """
        token = cache.get(self._token_cache_key_name())
        if not token:
            if self.can_refresh:
                self.refresh()
                token = cache.get(self._token_cache_key_name())
            else:
                raise TokenExpiredError()
        return token

    @access_token.setter
    def access_token(self, access_token):
        """
        Caches the access token.

        :param access_token: String access token for the Authorization request header.
        """
        cache.set(self._token_cache_key_name(), access_token, TOKEN_VALID_DURATION)
