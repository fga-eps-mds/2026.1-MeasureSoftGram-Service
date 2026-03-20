from django.contrib import admin, messages

from characteristics.models import (
    BalanceMatrix,
    CalculatedCharacteristic,
    SupportedCharacteristic,
)


@admin.register(SupportedCharacteristic)
class SupportedCharacteristicAdmin(admin.ModelAdmin):
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


@admin.register(SupportedCharacteristic.subcharacteristics.through)
class SubCharacteristicCharacteristicAssociation(admin.ModelAdmin):
    def changelist_view(self, request, extra_context=None):
        msg = (
            'Tabela que armazena a relação entre '
            'as CARACTERÍSTICAS e suas SUBCARACTERÍSTICAS.'
        )
        messages.add_message(request, messages.INFO, msg)
        return super().changelist_view(request, extra_context)

    # TODO: Descobrir como renomear essa tabela nas telas de admin
    class Meta:
        verbose_name = 'SubCharacteristic Characteristic Association'
        verbose_name_plural = 'SubCharacteristic Characteristic Association'

    list_display = (
        'id',
        'get_subcharacteristic_key',
        'get_characteristic_key',
    )
    search_fields = (
        'get_characteristic_key',
        'get_subcharacteristic_key',
    )
    list_filter = ('supportedcharacteristic',)

    def get_subcharacteristic_key(self, obj):
        return obj.supportedsubcharacteristic.key

    get_subcharacteristic_key.short_description = 'SubCharacteristic key'
    get_subcharacteristic_key.admin_order_field = (
        'supportedsubcharacteristic__key'
    )

    def get_characteristic_key(self, obj):
        return obj.supportedcharacteristic.key

    get_characteristic_key.short_description = 'Characteristic key'
    get_characteristic_key.admin_order_field = 'supportedcharacteristic__key'


@admin.register(BalanceMatrix)
class BalanceMatrixAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'source_characteristic',
        'target_characteristic',
        'relation_type',
    )
    search_fields = ('source_characteristic', 'target_characteristic')
    list_filter = ('source_characteristic', 'target_characteristic')


@admin.register(CalculatedCharacteristic)
class CalculatedCharacteristicAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'get_characteristic_key',
        'get_characteristic_name',
        'value',
        'created_at',
    )
    search_fields = (
        'characteristic__key',
        'characteristic__name',
    )
    list_filter = (
        'characteristic__name',
        'repository',
    )

    def get_characteristic_key(self, obj):
        return obj.characteristic.key

    get_characteristic_key.short_description = 'Characteristic key'
    get_characteristic_key.admin_order_field = 'characteristic__key'

    def get_characteristic_name(self, obj):
        return obj.characteristic.name

    get_characteristic_name.short_description = 'Characteristic name'
    get_characteristic_name.admin_order_field = 'characteristic__name'
