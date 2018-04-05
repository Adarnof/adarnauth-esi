from __future__ import unicode_literals


class TokenError(Exception):
    pass


class TokenInvalidError(TokenError):
    pass


class TokenExpiredError(TokenError):
    pass


class NotRefreshableTokenError(TokenError):
    pass


class IncompleteResponseError(Exception):
    pass
