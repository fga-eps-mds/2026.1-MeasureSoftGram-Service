from django.contrib import admin

from goals.models import Goal


@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'data',
    )
    search_fields = ('created_by',)
