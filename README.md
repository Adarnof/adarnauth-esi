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

### Specifying Resource Versions

As explained on the [EVE Developers Blog](https://developers.eveonline.com/blog/article/breaking-changes-and-you), it's best practice to call a specific version of the resource and allow the ESI router to map it to the correct route, being `legacy`, `latest` or `dev`. 

Client initialization begins with a base swagger spec. By default this is the version defined in settings (`ESI_API_VERSION`), but can be overridden with an extra argument to the factory:

    client = esi_client_factory(version='v4')
    client = token.get_esi_client(version='v4')

Only resources with the specified version number will be available. For instance, if you specify `v4` but `Universe` does not have a `v4` version, it will not be available to that specific client. Only `legacy`, `latest` and `dev` are guaranteed to have all resources available.

Individual resources are versioned and can be accessed by passing additional arguments to the factory:

    client = esi_client_factory(Universe='v1', Character='v3')
    client = token.get_esi_client(Universe='v1', Character='v3')

A list of available resources is available on the [EVE Swagger Interface browser](https://esi.tech.ccp.is). If the resource is not available with the specified version, an `AttributeError` will be raised. 

This version of the resource replaces the resource originally initialized. If the requested base version does not have the specified resource, it will be added.

Note that only one old revision of each resource is kept available through the legacy route. Keep an eye on the [deployment timeline](https://github.com/ccpgames/esi-issues/projects/2/) for resource updates.

### Using a Local Spec File

Specifying resource versions introduces one major problem for shared code: not all resources nor all their operations are available on any given version. This can be addressed by shipping a copy of the [versioned latest spec](https://esi.tech.ccp.is/_latest/swagger.json) with your app. **This is the preferred method for deployment.**

To build a client using this local spec, pass an additional kwarg `spec_file` which contains the path to your local swagger.json:

    c = esi_client_factory(spec_file='/path/to/swagger.json')

For example, a swagger.json in the current file's directory would look like:

    c = esi_client_factory(spec_file=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'swagger.json'))

If a `spec_file` is specified all other versioning is unavailable: ensure you ship a spec with resource versions your app can handle.

### Accessing Alternate Datasources
 
ESI datasource can also be specified during client creation:
 
    client = esi_client_factory(datasource='tranquility')
 
Available datasources are `tranquility` and `singularity`.

## Cleaning the Database

Two tasks are available:
 - `cleanup_callbackredirect` removes all `CallbackRedirect` models older than a specified age (in seconds). Default is 300.
 - `cleanup_token` checks all `Token` models, and if expired, attempts to refresh. If expired and cannot refresh, or fails to refresh, the model is deleted.

To schedule these automatically with celerybeat, add them to your settings.py `CELERYBEAT_SCHEDULE` dict like so:

    from celery.schedules import crontab
    
    CELERYBEAT_SCHEDULE = {
        ...
        'esi_cleanup_callbackredirect': {
            'task': 'esi.tasks.cleanup_callbackredirect',
            'schedule': crontab(hour='*/4'),
        },
        'esi_cleanup_token': {
            'task': 'esi.tasks.cleanup_token',
            'schedule': crontab(day_of_month='*/1'),
        },
    }

Recommended intervals are four hours for callback redirect cleanup and daily for token cleanup (token cleanup can get quite slow with a large database, so adjust as needed). If your app does not require background token validation, it may be advantageous to not schedule the token cleanup task, instead relying on the validation check when using `@token_required` decorators or adding `.require_valid()` to the end of a query.

## Operating on Singularity
 By defalt, adarnauth-esi process all operations on the tranquility cluster. To operate on singularity instead, two settings need to be changed:
  - `ESI_OAUTH_URL` should be set to `https://sisilogin.testeveonline.com/oauth`
  - `ESI_API_DATASOURCE` should be set to `singularity`
  
  Note that tokens cannot be transferred between servers. Any tokens in the database before switching to singularity will be deleted next refresh.
