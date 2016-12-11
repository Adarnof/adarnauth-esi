from __future__ import unicode_literals
from django.utils.encoding import python_2_unicode_compatible
from django.db import models
from esi import app_settings
from django.conf import settings
import requests
from django.utils import timezone
from esi.clients import esi_client_factory
import datetime
from requests_oauthlib import OAuth2Session
from esi.managers import TokenManager
from esi.errors import TokenInvalidError, NotRefreshableTokenError


@python_2_unicode_compatible
class Scope(models.Model):
    """
    Represents an access scope granted by SSO.
    """
    name = models.CharField(max_length=100, unique=True, help_text="The official EVE name for the scope.")
    help_text = models.TextField(help_text="The official EVE description of the scope.")

    @property
    def friendly_name(self):
        return self.name.split('.')[1]

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
    access_token = models.CharField(max_length=254, unique=True, help_text="The access token granted by SSO.")
    refresh_token = models.CharField(max_length=254, blank=True, null=True,
                                     help_text="A re-usable token to generate new access tokens upon expiry.")
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
                auth = requests.auth.HTTPBasicAuth(app_settings.ESI_SSO_CLIENT_ID, app_settings.ESI_SSO_CLIENT_SECRET)
            try:
                self.access_token = \
                    session.refresh_token(app_settings.ESI_TOKEN_URL, refresh_token=self.refresh_token, auth=auth)[
                        'access_token']
                self.created = timezone.now()
                self.save()
            except requests.HTTPError:
                raise TokenInvalidError()
        else:
            raise NotRefreshableTokenError()

    def get_esi_client(self):
        """
        Creates an authenticated ESI client with this token.
        :return: :class:`bravado.client.SwaggerClient`
        """
        return esi_client_factory(token=self)


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
