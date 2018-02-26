# adarnauth-esi
Django app for accessing the EVE Swagger Interface.

## Quick Start

1. Add `esi` to your `INSTALLED_APPS` setting:

   
    INSTALLED_APPS += ['esi']

2. Include the esi urlconf in your project's urls:


    url(r'^sso/', include('esi.urls', namespace='esi')),

3. Register an application with the [EVE Developers site](https://developers.eveonline.com/applications)

    If your application requires scopes, select `Authenticated API Access` and register all possible scopes your app can request. Otherwise `Authentication Only` will suffice.
    Set the `Callback URL` to `https://example.com/sso/callback/`

4. Add SSO client settings to your project settings:


    ESI_SSO_CLIENT_ID = "my client id"    
    ESI_SSO_CLIENT_SECRET = "my client secret"
    ESI_SSO_CALLBACK_URL = "https://example.com/sso/callback"
    

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

This app provides an extension of the [bravado SwaggerClient](https://github.com/Yelp/bravado).

### Getting a Client

A SwaggerClient can be created from a URL to a swagger spec or a path to a local file:

    from esi.clients import SwaggerClient
    client = SwaggerClient.from_url('https://esi.tech.ccp.is/_latest/swagger.json')
    client = SwaggerClient.from_file('/home/adarnof/swagger.json')

### Accessing an Endpoint

Endpoints are grouped based on their resource (the category on the [swagger spec browser](https://esi.tech.ccp.is)).

Endpoints ("operations") are called by first accessing their resource and then calling the operation. Arguments are passed as keywords:

    future = client.Character.get_characters_character_id(character_id=234899860)

This returns a prepared request (a "future"). The actual result can be called by evaluating the future:

    return = future.result()

Endpoint results are returned as a dictionary.

### Accessing Authenticated Endpoints
 
The SwaggerClient comes with a context manager for temporarily adding authentication:

    with client.authenticate(my_token) as auth_client:
        return auth_client.Resource.this_endpoint_requires_authorization().result()

This allows a single initialized SwaggerClient to authenticate with multiple tokens over its lifetime. 

Authenticated clients will auto-renew tokens when needed, or raise a `TokenExpiredError` if they aren't renewable.