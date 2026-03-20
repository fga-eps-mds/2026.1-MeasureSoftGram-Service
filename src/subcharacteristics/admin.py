from django.contrib import admin, messages

from subcharacteristics.models import (
    CalculatedSubCharacteristic,
    SupportedSubCharacteristic,
)


@admin.register(SupportedSubCharacteristic)
class SupportedSubCharacteristicAdmin(admin.ModelAdmin):
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


@admin.register(SupportedSubCharacteristic.measures.through)
class MeasureSubCharacteristicAssociation(admin.ModelAdmin):
    def changelist_view(self, request, extra_context=None):
        msg = (
            'Tabela que armazena a relação entre '
            'as SUBCARACTERÍSTICAS e suas MEDIDAS.'
        )
        messages.add_message(request, messages.INFO, msg)
        return super().changelist_view(request, extra_context)

    # TODO: Descobrir como renomear essa tabela nas telas de admin
    class Meta:
        verbose_name = 'Measure SubCharacteristic Association'
        verbose_name_plural = 'Measure SubCharacteristic Association'

    list_display = (
        'id',
        'get_measure_key',
        'get_subcharacteristic_key',
    )
    search_fields = (
        'get_measure_key',
        'get_subcharacteristic_key',
    )
    list_filter = ('supportedsubcharacteristic',)

    def get_subcharacteristic_key(self, obj):
        return obj.supportedsubcharacteristic.key

    get_subcharacteristic_key.short_description = 'SubCharacteristic key'
    get_subcharacteristic_key.admin_order_field = (
        'supportedsubcharacteristic__key'
    )

    def get_measure_key(self, obj):
        return obj.supportedmeasure.key

    get_measure_key.short_description = 'Measure key'
    get_measure_key.admin_order_field = 'supportedmeasure__key'


@admin.register(CalculatedSubCharacteristic)
class CalculatedSubCharacteristicAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'get_subcharacteristic_key',
        'get_subcharacteristic_name',
        'value',
        'created_at',
    )
    search_fields = (
        'subcharacteristic__key',
        'subcharacteristic__name',
    )
    list_filter = (
        'repository',
        'subcharacteristic__name',
    )

    def get_subcharacteristic_key(self, obj):
        return obj.subcharacteristic.key

    get_subcharacteristic_key.short_description = 'SubCharacteristic key'
    get_subcharacteristic_key.admin_order_field = 'subcharacteristic__key'

    def get_subcharacteristic_name(self, obj):
        return obj.subcharacteristic.name

    get_subcharacteristic_name.short_description = 'SubCharacteristic name'
    get_subcharacteristic_name.admin_order_field = 'subcharacteristic__name'
