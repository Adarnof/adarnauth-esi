# adarnauth-esi
Django app for accessing the EVE Swagger Interface.

## Quick Start

1. Add `esi` to your `INSTALLED_APPS` setting:


    INSTALLED_APPS = [
        ...
        'esi',
    ]

2. Include the esi urlconf in your project's urls:


    url(r'^sso/', include('esi.urls'), namespace='esi'),

3. Register an application with the [EVE Developers site](https://developers.eveonline.com/applications)

If your application requires scopes, select `CREST Access` and register all possible scopes your app can request. Otherwise `Authentication Only` will suffice.
Set the `Callback URL` to `https://example.com/sso/callback`

4. Add SSO client settings to your project settings:


    ESI_SSO_CLIENT_ID = "my client id"
    ESI_SSO_CLIENT_SECRET = "my client secret    
    ESI_SSO_CALLBACK_URL = "https://example.com/sso/callback"
    

5. Run `python manage.py migrate` to create models.

## Usage in Views

When views require a token, wrap with the `token_required` decorator:

    from esi.decorators import token_required

    @token_required()
    def my_view(request, tokens):
        ...

To specify scopes, add either a list of names or a space-delimited string:

    @token_required(scopes=['read_skills', 'read_clones'])
    @token_required(scopes='read_skills read_clones')

To require a new token, such as for logging in, add the `new` argument:

    @token_required(new=True)

## Accessing the EVE Swagger Interface

adarnauth-esi provides a convenience wrapper around the [bravado SwaggerClient](https://github.com/Yelp/bravado).

### Getting a Client

To get a SwaggerClient configured for ESI, call the factory:

    from esi.client import esi_client_factory
    client = esi_client_factory()

### Accessing Authenticated Endpoints

To get an authenticated SwaggerClient, add the token argument:

    client = esi_client_factory(token=my_token)

Or, get the client from the specific token model instead:

    client = my_token.get_esi_client()

Authenticated clients will auto-renew tokens when needed, or raise a `TokenExpiredError` if they aren't renewable.

## Cleaning the Database

If you have celerybeat running, two tasks are automatically scheduled:
 - `cleanup_callbackredirect` removes all `CallbackRedirect` models older than a specified age (in seconds). Default is 300, runs every 4 hours.
 - `cleanup_token` checks all `Token` models, and if expired, attempts to refresh. If expired and cannot refresh, or fails to refresh, the model is deleted. Runs every day.