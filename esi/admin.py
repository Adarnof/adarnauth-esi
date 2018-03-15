from __future__ import unicode_literals
from django.contrib import admin
from .models import Token, Scope
from django.contrib.auth import get_user_model


@admin.register(Scope)
class ScopeAdmin(admin.ModelAdmin):
    list_display = ('name', 'help_text')


@admin.register(Token)
class TokenAdmin(admin.ModelAdmin):
    def get_scopes(self, obj):
        return ", ".join([x.name for x in obj.scopes.all()])

    get_scopes.short_description = 'Scopes'

    list_display = ('user', 'character_name', 'get_scopes')

    User = get_user_model()
    search_fields = ['user__%s' % User.USERNAME_FIELD, 'character_name', 'scopes__name']
