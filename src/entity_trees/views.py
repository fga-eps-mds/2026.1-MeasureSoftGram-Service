"""
Módulo que agrupa as views relacionadas à árvore de entidades. Quando dizemos
árvore de entidades, estamos falando do relacionamentos entre as entidades.
Isso é:
* Características com subcaracterísticas
* Subcaracterísticas com medidas
"""
from rest_framework import mixins, viewsets
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from characteristics.models import SupportedCharacteristic
from entity_trees.serializers import (
    CharacteristicEntityRelationshipTreeSerializer,
    pre_config_to_entity_tree,
)
from organizations.models import Product
from release_configuration.models import ReleaseConfiguration


class SupportedEntitiesRelationshipTreeViewSet(
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """
    ViewSet as entidades suportadas e suas relações no formato de árvore
    """

    serializer_class = CharacteristicEntityRelationshipTreeSerializer
    queryset = SupportedCharacteristic.objects.all()

    def list(self, request, *args, **kwargs):
        qs = SupportedCharacteristic.objects.all().prefetch_related(
            'subcharacteristics',
            'subcharacteristics__measures',
        )

        serializer = CharacteristicEntityRelationshipTreeSerializer(
            qs,
            many=True,
        )

        return Response(serializer.data)


class ReleaseConfigurationEntitiesRelationshipTreeViewSet(
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """
    Viewset que retorna as entidades de uma pré-configução e
    suas relações no formato de árvore
    """

    serializer_class = CharacteristicEntityRelationshipTreeSerializer
    queryset = SupportedCharacteristic.objects.all()

    def get_product(self):
        return get_object_or_404(
            Product,
            id=self.kwargs['product_pk'],
            organization_id=self.kwargs['organization_pk'],
        )

    def list(self, request, *args, **kwargs):
        product = self.get_product()
        current_pre_config = product.release_configuration.first()
        entity_tree = pre_config_to_entity_tree(current_pre_config)
        return Response(entity_tree)
