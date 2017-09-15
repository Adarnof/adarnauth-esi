from __future__ import unicode_literals
from django.utils.encoding import python_2_unicode_compatible
from django.db import models
from esi import app_settings
from django.conf import settings
from requests.auth import HTTPBasicAuth
from django.utils import timezone
from esi.clients import esi_client_factory
import datetime
from requests_oauthlib import OAuth2Session
from esi.managers import TokenManager
from esi.errors import TokenInvalidError, NotRefreshableTokenError, TokenExpiredError
from oauthlib.oauth2.rfc6749.errors import InvalidGrantError, MissingTokenError, InvalidClientError
from django.core.exceptions import ImproperlyConfigured


@python_2_unicode_compatible
class Scope(models.Model):
    """
    Represents an access scope granted by SSO.
    """
    name = models.CharField(max_length=100, unique=True, help_text="The official EVE name for the scope.")
    help_text = models.TextField(help_text="The official EVE description of the scope.")

    @property
    def friendly_name(self):
        try:
            return self.name.split('.')[1]
        except IndexError:
            return self.name

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class Token(models.Model):
    """
    EVE Swagger Interface Access Token
    Contains information about the authenticating character and scopes granted to this token.
    Contains the access token required for ESI authentication as well as refreshing.
    """

    created = models.DateTimeField(auto_now_add=True)
    access_token = models.CharField(max_length=254, help_text="The access token granted by SSO.",
                                    editable=False)
    refresh_token = models.CharField(max_length=254, blank=True, null=True,
                                     help_text="A re-usable token to generate new access tokens upon expiry.",
                                     editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, blank=True, null=True,
                             help_text="The user to whom this token belongs.")
    character_id = models.IntegerField(help_text="The ID of the EVE character who authenticated by SSO.")
    character_name = models.CharField(max_length=100,
                                      help_text="The name of the EVE character who authenticated by SSO.")
    token_type = models.CharField(max_length=100, choices=(('Character', 'Character'), ('Corporation', 'Corporation'),),
                                  default='Character', help_text="The applicable range of the token.")
    character_owner_hash = models.CharField(max_length=254,
                                            help_text="The unique string identifying this character and its owning EVE "
                                                      "account. Changes if the owning account changes.")
    scopes = models.ManyToManyField(Scope, blank=True, help_text="The access scopes granted by this token.")

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
    def can_refresh(self):
        """
        Determines if this token can be refreshed upon expiry
        """
        return bool(self.refresh_token)

    @property
    def expires(self):
        """
        Determines when the token expires.
        """
        return self.created + datetime.timedelta(seconds=app_settings.ESI_TOKEN_VALID_DURATION)

    @property
    def expired(self):
        """
        Determines if the access token has expired.
        """
        return self.expires < timezone.now()

    def refresh(self, session=None, auth=None):
        """
        Refreshes the token.
        :param session: :class:`requests_oauthlib.OAuth2Session` for refreshing token with.
        :param auth: :class:`requests.auth.HTTPBasicAuth`
        """
        if self.can_refresh:
            if not session:
                session = OAuth2Session(app_settings.ESI_SSO_CLIENT_ID)
            if not auth:
                auth = HTTPBasicAuth(app_settings.ESI_SSO_CLIENT_ID, app_settings.ESI_SSO_CLIENT_SECRET)
            try:
                self.access_token = \
                    session.refresh_token(app_settings.ESI_TOKEN_URL, refresh_token=self.refresh_token, auth=auth)[
                        'access_token']
                self.created = timezone.now()
                self.save()
            except (InvalidGrantError, MissingTokenError):
                raise TokenInvalidError()
            except InvalidClientError:
                raise ImproperlyConfigured('Verify ESI_SSO_CLIENT_ID and ESI_SSO_CLIENT_SECRET settings.')
        else:
            raise NotRefreshableTokenError()

    def get_esi_client(self, **kwargs):
        """
        Creates an authenticated ESI client with this token.
        :param kwargs: Extra spec versioning as per `esi.clients.esi_client_factory`
        :return: :class:`bravado.client.SwaggerClient`
        """
        return esi_client_factory(token=self, **kwargs)

    @classmethod
    def get_token_data(cls, access_token):
        session = OAuth2Session(app_settings.ESI_SSO_CLIENT_ID, token={'access_token': access_token})
        return session.request('get', app_settings.ESI_TOKEN_VERIFY_URL).json()

    def update_token_data(self, commit=True):
        if self.expired:
            if self.can_refresh:
                self.refresh()
            else:
                raise TokenExpiredError()
        token_data = self.get_token_data(self.access_token)
        self.character_id = token_data['CharacterID']
        self.character_name = token_data['CharacterName']
        self.character_owner_hash = token_data['CharacterOwnerHash']
        self.token_type = token_data['TokenType']
        if commit:
            self.save()


@python_2_unicode_compatible
class CallbackRedirect(models.Model):
    """
    Records the intended destination for the SSO callback.
    Used to internally redirect SSO callbacks.
    """
    url = models.CharField(max_length=254, default='/', help_text="The internal URL to redirect this callback towards.")
    session_key = models.CharField(max_length=254, unique=True,
                                   help_text="Session key identifying the session this redirect was created for.")
    state = models.CharField(max_length=128, help_text="OAuth2 state string representing this session.")
    created = models.DateTimeField(auto_now_add=True)
    token = models.ForeignKey(Token, blank=True, null=True,
                              help_text="Token generated by a completed code exchange from callback processing.")

    def __str__(self):
        return "%s: %s" % (self.session_key, self.url)

    def __repr__(self):
        return "<{}(id={}): {} to {}>".format(self.__class__.__name__, self.pk, self.session_key, self.url)
