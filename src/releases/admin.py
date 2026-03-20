from django.contrib import admin

from releases.models import Release


@admin.register(Release)
class GoalAdmin(admin.ModelAdmin):
    list_display = (
        'start_at',
        'end_at',
        'release_name',
        'goal',
    )
    search_fields = ('release_name',)
