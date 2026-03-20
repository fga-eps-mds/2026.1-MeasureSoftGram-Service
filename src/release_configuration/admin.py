from django.contrib import admin

from release_configuration.models import ReleaseConfiguration


@admin.register(ReleaseConfiguration)
class ReleaseConfigurationurationAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'name',
        'created_at',
        'product',
    )
    search_fields = ('name',)
    list_filter = ('product',)
