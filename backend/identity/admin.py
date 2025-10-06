from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from django.utils.translation import gettext_lazy as _

from .models import ApiClient, OAuthProvider

User = get_user_model()

# Unregister the original Group admin
admin.site.unregister(Group)

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    A custom UserAdmin to match the custom User model.
    """
    ordering = ['email']
    list_display = ('email', 'username', 'full_name', 'is_staff', 'is_active')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups')
    search_fields = ('email', 'username', 'full_name')
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal info'), {'fields': ('username', 'full_name')}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )

@admin.register(ApiClient)
class ApiClientAdmin(admin.ModelAdmin):
    list_display = ('name', 'tenant', 'key')
    search_fields = ('name', 'tenant__name')

@admin.register(OAuthProvider)
class OAuthProviderAdmin(admin.ModelAdmin):
    list_display = ('kind', 'tenant')
    list_filter = ('kind',)
