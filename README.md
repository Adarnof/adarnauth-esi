# adarnauth-esi
Django app for accessing the EVE Swagger Interface.

## Quick Start

1. Add `esi` to your `INSTALLED_APPS` setting:

   `INSTALLED_APPS += 'esi'`

2. Include the esi urlconf in your project's urls:

    `url(r'^sso/', include('esi.urls'), namespace='esi'),`

3. Register an application with the [EVE Developers site](https://developers.eveonline.com/applications)

    If your application requires scopes, select `Authenticated API Access` and register all possible scopes your app can request. Otherwise `Authentication Only` will suffice.
    Set the `Callback URL` to `https://example.com/sso/callback`

4. Add SSO client settings to your project settings:

    `ESI_SSO_CLIENT_ID = "my client id"`
    
    `ESI_SSO_CLIENT_SECRET = "my client secret"`
    
    `ESI_SSO_CALLBACK_URL = "https://example.com/sso/callback"`
    

5. Run `python manage.py migrate` to create models.

## Usage in Views

When views require a token, wrap with the `token_required` decorator and accept a `token` arg:

    from esi.decorators import token_required

    @token_required()
    def my_view(request, token):
        ...

This will prompt the user to either select a token from their current ones, or if none exist create a new one via SSO.

To specify scopes, add either a list of names or a space-delimited string:

    @token_required(scopes=['esi-location.read_ship_type.v1', 'esi-location.read_location.v1'])
    @token_required(scopes='esi-location.read_ship_type.v1 esi-location.read_location.v1')

To require a new token, such as for logging in, add the `new` argument:

    @token_required(new=True)

To request all of a user's tokens which have the required scopes, wrap instead with the `tokens_required` decorator and accept a `tokens` arg:

    @tokens_required(scopes='esi-location.read_ship_type.v1')
    def my_view(request, tokens):
        ...

This skips prompting for token selection and instead passes that responsibility to the view. Tokens are provided as a queryset.

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

### Accessing API Versions

To get a SwaggerClient to access specific versions of resources, pass a `version` argument. Versions must be one of `legacy`, `latest`, `dev`, or a specific version number such as `v4`.

    client = esi_client_factory(version='v4')
    client = token.get_esi_client(version='v4')

Only resources with the specified version number will be available. For instance, if you access `v4` but `Universe` doesn't have a `v4` version, it will not be available to that specific client. It's best to only use `legacy`, `latest`, or `dev` for this.

### Accessing Resource Versions

Individual resources are versioned and can be accessed by passing additional arguments to the factory:

    client = esi_client_factory(Universe='v1', Character='v3')
    client = token.get_esi_client(Universe='v1', Character='v3')

Versions not available for the given resource will raise an `AttributeError`. Any resources without an explicit versions will be provided at the `version` revision (see above notes, default is `ESI_API_VERSION`). 

Learn more about alt routes from the [EVE Developers Blog](https://developers.eveonline.com/blog/article/breaking-changes-and-you)

### Accessing Alternate Datasources
 
ESI datasource can also be specified during client creation:
 
    client = esi_client_factory(datasource='tranquility')
 
Available datasources are `tranquility` and `singularity`.

## Cleaning the Database

If you have celerybeat running, two tasks are automatically scheduled:
 - `cleanup_callbackredirect` removes all `CallbackRedirect` models older than a specified age (in seconds). Default is 300, runs every 4 hours.
 - `cleanup_token` checks all `Token` models, and if expired, attempts to refresh. If expired and cannot refresh, or fails to refresh, the model is deleted. Runs every day.

## Operating on Singularity
 By defalt, adarnauth-esi process all operations on the tranquility cluster. To operate on singularity instead, two settings need to be changed:
  - `ESI_OAUTH_URL` should be set to `https://sisilogin.testeveonline.com/oauth`
  - `ESI_API_DATASOURCE` should be set to `singularity`
  
  Note that tokens cannot be transferred between servers. Any tokens in the database befure switching to singularity will be deleted next refresh.
