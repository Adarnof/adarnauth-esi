from __future__ import unicode_literals
from django.db import models
from requests_oauthlib import OAuth2Session
from esi import app_settings
import requests
from django.utils import timezone
from datetime import timedelta
from django.utils.six import string_types
from esi.errors import TokenError, IncompleteResponseError
import logging

logger = logging.getLogger(__name__)


def _process_scopes(scopes):
    if scopes is None:
        # support filtering by no scopes with None passed
        scopes = []
    if not isinstance(scopes, models.QuerySet) and len(scopes) == 1:
        # support a single space-delimited string inside a list because :users:
        scopes = scopes[0]
    # support space-delimited string scopes or lists
    if isinstance(scopes, string_types):
        scopes = set(scopes.split())
    return set(str(s) for s in scopes)


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
        Excludes tokens for which the refresh was incomplete for other reasons.
        """
        session = OAuth2Session(app_settings.ESI_SSO_CLIENT_ID)
        auth = requests.auth.HTTPBasicAuth(app_settings.ESI_SSO_CLIENT_ID, app_settings.ESI_SSO_CLIENT_SECRET)
        incomplete = []
        for model in self.filter(refresh_token__isnull=False):
            try:
                model.refresh(session=session, auth=auth)
                logging.debug("Successfully refreshed {0}".format(repr(model)))
            except TokenError:
                logger.info("Refresh failed for {0}. Deleting.".format(repr(model)))
                model.delete()
            except IncompleteResponseError:
                incomplete.append(model.pk)
        self.filter(refresh_token__isnull=True).get_expired().delete()
        return self.exclude(pk__in=incomplete)

    def require_valid(self):
        """
        Ensures all tokens are still valid. If expired, attempts to refresh.
        Deletes those which fail to refresh or cannot be refreshed.
        :return: All tokens which are still valid.
        :rtype: :class:`esi.managers.TokenQueryset`
        """
        expired = self.get_expired()
        valid = self.exclude(pk__in=expired)
        valid_expired = expired.bulk_refresh()
        return valid_expired | valid

    def require_scopes(self, scope_string):
        """
        :param scope_string: The required scopes.
        :type scope_string: Union[str, list]
        :return: The tokens with all requested scopes.
        :rtype: :class:`esi.managers.TokenQueryset`
        """
        scopes = _process_scopes(scope_string)
        if not scopes:
            # asking for tokens with no scopes
            return self.filter(scopes__isnull=True)
        from .models import Scope
        scope_pks = Scope.objects.filter(name__in=scopes).values_list('pk', flat=True)
        if not len(scopes) == len(scope_pks):
            # there's a scope we don't recognize, so we can't have any tokens for it
            return self.none()
        tokens = self.all()
        for pk in scope_pks:
            tokens = tokens.filter(scopes__pk=pk)
        return tokens

    def require_scopes_exact(self, scope_string):
        """
        :param scope_string: The required scopes.
        :type scope_string: Union[str, list]
        :return: The tokens with only the requested scopes.
        :rtype: :class:`esi.managers.TokenQueryset`
        """
        num_scopes = len(_process_scopes(scope_string))
        pks = [v['pk'] for v in self.annotate(models.Count('scopes')).require_scopes(scope_string).filter(
            scopes__count=num_scopes).values('pk', 'scopes__id')]
        return self.filter(pk__in=pks)

    def equivalent_to(self, token):
        """
        Gets all tokens which match the character and scopes of a reference token
        :param token: :class:`esi.models.Token`
        :return: :class:`esi.managers.TokenQueryset`
        """
        return self.filter(character_id=token.character_id).require_scopes_exact(token.scopes.all()).filter(
            models.Q(user=token.user) | models.Q(user__isnull=True)).exclude(pk=token.pk)


class TokenManager(models.Manager):
    def get_queryset(self):
        """
        Replace base queryset model with custom TokenQueryset
        :rtype: :class:`esi.managers.TokenQueryset`
        """
        return TokenQueryset(self.model, using=self._db)

    def create_from_code(self, code, user=None):
        """
        Perform OAuth code exchange to retrieve a token.
        :param code: OAuth grant code.
        :param user: User who will own token.
        :return: :class:`esi.models.Token`
        """

        # perform code exchange
        logger.debug("Creating new token from code {0}".format(code[:-5]))
        oauth = OAuth2Session(app_settings.ESI_SSO_CLIENT_ID, redirect_uri=app_settings.ESI_SSO_CALLBACK_URL)
        token = oauth.fetch_token(app_settings.ESI_TOKEN_URL, client_secret=app_settings.ESI_SSO_CLIENT_SECRET,
                                  code=code)
        r = oauth.request('get', app_settings.ESI_TOKEN_VERIFY_URL)
        r.raise_for_status()
        token_data = r.json()
        logger.debug(token_data)

        # translate returned data to a model
        model = self.create(
            character_id=token_data['CharacterID'],
            character_name=token_data['CharacterName'],
            character_owner_hash=token_data['CharacterOwnerHash'],
            access_token=token['access_token'],
            refresh_token=token['refresh_token'],
            token_type=token_data['TokenType'],
            user=user,
        )

        # parse scopes
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
            logger.debug("Added {0} scopes to new token.".format(model.scopes.all().count()))

        if not app_settings.ESI_ALWAYS_CREATE_TOKEN:
            # see if we already have a token for this character and scope combination
            # if so, we don't need a new one
            queryset = self.get_queryset().equivalent_to(model)
            if queryset.exists():
                logger.debug(
                    "Identified {0} tokens equivalent to new token. Updating access and refresh tokens.".format(
                        queryset.count()))
                queryset.update(
                    access_token=model.access_token,
                    refresh_token=model.refresh_token,
                    created=model.created,
                )
                if queryset.filter(user=model.user).exists():
                    logger.debug("Equivalent token with same user exists. Deleting new token.")
                    model.delete()
                    model = queryset.filter(user=model.user)[0]  # pick one at random

        logger.debug("Successfully created {0} for user {1}".format(repr(model), user))
        return model

    def create_from_request(self, request):
        """
        Generate a token from the OAuth callback request. Must contain 'code' in GET.
        :param request: OAuth callback request.
        :return: :class:`esi.models.Token`
        """
        logger.debug("Creating new token for {0} session {1}".format(request.user, request.session.session_key[:5]))
        code = request.GET.get('code')
        # attach a user during creation for some functionality in a post_save created receiver I'm working on elsewhere
        model = self.create_from_code(code, user=request.user if request.user.is_authenticated else None)
        return model
