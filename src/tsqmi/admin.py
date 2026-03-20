from django.contrib import admin

from tsqmi.models import TSQMI


@admin.register(TSQMI)
class TSQMIAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'value',
        'created_at',
        'repository',
    )

    list_filter = ('repository',)
