from django.contrib import admin, messages

from measures.models import CalculatedMeasure, SupportedMeasure


@admin.register(SupportedMeasure)
class SupportedMeasureAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'key',
        'name',
        'description',
    )
    search_fields = (
        'key',
        'name',
    )
    filter_horizontal = ('metrics',)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.prefetch_related('metrics')
        return queryset


@admin.register(CalculatedMeasure)
class CalculatedMeasureAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'get_measure_key',
        'get_measure_name',
        'value',
        'created_at',
    )
    search_fields = (
        'measure__key',
        'measure__name',
    )
    list_filter = (
        'repository',
        'measure__name',
    )

    def get_measure_name(self, obj):
        return obj.measure.name

    get_measure_name.short_description = 'Measure name'
    get_measure_name.admin_order_field = 'measure__name'

    def get_measure_key(self, obj):
        return obj.measure.key

    get_measure_key.short_description = 'Measure key'
    get_measure_key.admin_order_field = 'measure__key'


@admin.register(SupportedMeasure.metrics.through)
class MetricsMeasuresAssociation(admin.ModelAdmin):
    """
    Tabela administrativa para permitir a visualização
    das associações entre medidas e métricas.
    """

    def changelist_view(self, request, extra_context=None):
        msg = (
            'Tabela que armazena a relação entre '
            'as MEDIDAS e suas MÉTRICAS.'
        )
        messages.add_message(request, messages.INFO, msg)
        return super().changelist_view(request, extra_context)

    # TODO: Descobrir como renomear essa tabela nas telas de admin
    class Meta:
        verbose_name = 'Metrics Measure Association'
        verbose_name_plural = 'Metrics Measure Association'

    list_display = (
        'id',
        'get_metric_key',
        'get_measure_key',
    )
    search_fields = (
        'get_metric_key',
        'get_measure_key',
    )
    list_filter = ('supportedmeasure',)

    def get_metric_key(self, obj):
        return obj.supportedmetric.key

    get_metric_key.short_description = 'Metric key'
    get_metric_key.admin_order_field = 'supportedmetric__key'

    def get_measure_key(self, obj):
        return obj.supportedmeasure.key

    get_measure_key.short_description = 'Measure key'
    get_measure_key.admin_order_field = 'supportedmeasure__key'
