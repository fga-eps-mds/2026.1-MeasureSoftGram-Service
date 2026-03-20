from rest_framework import mixins, permissions, viewsets
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from drf_yasg.utils import swagger_auto_schema

from organizations.models import Organization, Product, Repository
from organizations.serializers import (
    OrganizationSerializer,
    ProductSerializer,
    RepositoriesTSQMIHistorySerializer,
    RepositorySerializer,
    RepositoryTSQMILatestValueSerializer,
)


class OrganizationViewSet(viewsets.ModelViewSet):
    queryset = (
        Organization.objects.all().order_by('id').prefetch_related('products')
    )
    serializer_class = OrganizationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(admin=self.request.user)


class ProductViewSet(viewsets.ModelViewSet):
    queryset = (
        Product.objects.all()
        .order_by('-id')
        .select_related('organization')
        .prefetch_related('repositories')
    )
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_organization(self):
        return get_object_or_404(
            Organization,
            id=self.kwargs['organization_pk'],
        )

    def get_queryset(self):
        qs = (
            Product.objects.all()
            .order_by('-id')
            .select_related('organization')
            .prefetch_related('repositories')
        )
        return qs.filter(organization=self.kwargs['organization_pk'])

    def perform_create(self, serializer):
        serializer.save(organization_id=self.kwargs['organization_pk'])


class RepositoryViewSetMixin:
    permission_classes = [permissions.IsAuthenticated]

    def get_product(self):
        return get_object_or_404(
            Product,
            id=self.kwargs['product_pk'],
            organization_id=self.kwargs['organization_pk'],
        )


class RepositoryViewSet(
    RepositoryViewSetMixin,
    viewsets.ModelViewSet,
):
    serializer_class = RepositorySerializer
    queryset = Repository.objects.all()

    def perform_create(self, serializer):
        serializer.is_valid(raise_exception=True)
        product = self.get_product()
        serializer.save(product=product)

    def get_queryset(self):
        qs = Repository.objects.all().order_by('-id').select_related('product')
        return qs.filter(product=self.kwargs['product_pk'])


class RepositoriesTSQMILatestValueViewSet(
    RepositoryViewSetMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """
    Lista o TSQMI mais recente dos repositórios de um produto
    """

    serializer_class = RepositoryTSQMILatestValueSerializer
    queryset = Repository.objects.all()

    def get_queryset(self):
        product = self.get_product()
        qs = product.repositories.all()
        qs = qs.order_by('-id')
        qs = qs.prefetch_related(
            'calculated_tsqmis',
            'product',
            'product__organization',
        )
        return qs


class RepositoriesTSQMIHistoryViewSet(
    RepositoryViewSetMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = RepositoriesTSQMIHistorySerializer
    queryset = Repository.objects.all()

    def get_queryset(self):
        product = self.get_product()
        qs = product.repositories.all()
        qs = qs.prefetch_related(
            'calculated_tsqmis',
            'product',
            'product__organization',
        )
        return qs
