import datetime as dt

from django.contrib import admin

from metrics.models import CollectedMetric, SupportedMetric


@admin.register(SupportedMetric)
class SupportedMetricAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'key',
        'name',
        'metric_type',
        'description',
    )
    search_fields = (
        'key',
        'name',
    )
    list_filter = ('metric_type',)


@admin.register(CollectedMetric)
class CollectedMetricAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'get_metric_key',
        'get_metric_name',
        'get_value',
        'path',
        'dynamic_key',
        'created_at',
    )
    search_fields = (
        'metric__key',
        'path',
    )
    list_filter = (
        'repository',
        'qualifier',
        'metric__metric_type',
        'metric__name',
    )

    def get_metric_name(self, obj: CollectedMetric):
        return obj.metric.name

    get_metric_name.short_description = 'Metric name'
    get_metric_name.admin_order_field = 'metric__name'

    def get_metric_key(self, obj: CollectedMetric):
        return obj.metric.key

    get_metric_key.short_description = 'Metric key'
    get_metric_key.admin_order_field = 'metric__key'

    def get_value(self, obj: CollectedMetric):
        value = obj.value

        millisec_type = SupportedMetric.SupportedMetricTypes.MILLISEC

        if obj.metric.metric_type == millisec_type:
            value = dt.datetime.fromtimestamp(value)

        return value

    get_value.short_description = 'Value'
    get_value.admin_order_field = 'value'
