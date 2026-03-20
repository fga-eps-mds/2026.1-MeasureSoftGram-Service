from django.contrib import admin
from django.contrib.auth.forms import AdminPasswordChangeForm
from django.utils.translation import gettext_lazy as _

from accounts.models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'username',
        'email',
        'is_staff',
        'is_active',
        'is_superuser',
        'last_login',
        'date_joined',
    )

    search_fields = (
        'username',
        'email',
        'first_name',
        'last_name',
    )

    filter_horizontal = (
        'groups',
        'user_permissions',
    )

    ordering = ('username',)

    add_fieldsets = (
        (
            None,
            {
                'classes': ('wide',),
                'fields': ('username', 'password1', 'password2'),
            },
        ),
        (
            _('Permissions'),
            {
                'fields': (
                    'is_active',
                    'is_staff',
                    'is_superuser',
                    'groups',
                    'user_permissions',
                ),
            },
        ),
    )
