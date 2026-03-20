import logging
from django.conf import settings
from rest_framework import serializers
from rest_framework.reverse import reverse
from rest_framework.validators import UniqueValidator
from organizations.models import Organization, Product, Repository
from tsqmi.models import TSQMI
from tsqmi.serializers import TSQMISerializer
from django.core.exceptions import ValidationError
import requests
from requests.exceptions import RequestException
from urllib.parse import urlparse


class OrganizationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ('name',)

    def save(self, **kwargs):
        user = self.context['request'].user
        organization = Organization.objects.create(
            admin=user, **self.validated_data
        )
        return organization


class OrganizationSerializer(serializers.HyperlinkedModelSerializer):
    products = serializers.SerializerMethodField()
    actions = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = (
            'id',
            'url',
            'name',
            'description',
            'products',
            'actions',
        )
        extra_kwargs = {
            'name': {
                'validators': [
                    UniqueValidator(
                        queryset=Organization.objects.all(),
                        message='Organization with this name already exists.',
                    )
                ]
            },
        }

    def get_products(self, obj: Organization):
        products_urls = []
        for product in obj.products.all():
            url = reverse(
                'product-detail',
                kwargs={
                    'pk': product.id,
                    'organization_pk': obj.id,
                },
                request=self.context['request'],
            )
            products_urls.append(url)
        return products_urls

    def get_actions(self, obj: Organization):
        create_a_new_product_url = reverse(
            'product-list',
            kwargs={
                'organization_pk': obj.id,
            },
            request=self.context['request'],
        )

        return {
            'create a new product': create_a_new_product_url,
        }


class ProductSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    repositories = serializers.SerializerMethodField()
    actions = serializers.SerializerMethodField()

    organization = serializers.HyperlinkedRelatedField(
        view_name='organization-detail',
        read_only=True,
    )

    gaugeRedLimit = serializers.DecimalField(
        coerce_to_string=False,
        max_digits=3,
        decimal_places=2,
        required=False,
        allow_null=True,
    )
    gaugeYellowLimit = serializers.DecimalField(
        coerce_to_string=False,
        max_digits=3,
        decimal_places=2,
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Product
        fields = (
            'id',
            'url',
            'name',
            'description',
            'repositories',
            'actions',
            'organization',
            'gaugeRedLimit',
            'gaugeYellowLimit',
        )
        extra_kwargs = {
            'key': {'read_only': True},
        }

    def validate(self, attrs):
        """
        Valida se o nome do produto é único para a organização
        """
        name = attrs['name']
        organization = self.context['view'].get_organization()
        product_id = self.instance.id if self.instance else None

        qs = Product.objects.filter(
            name=name, organization=organization
        ).exclude(id=product_id)

        if qs.exists():
            raise serializers.ValidationError(
                'Product with this name already exists.'
            )

        return attrs

    def get_url(self, obj):
        """
        Retorna a URL desse produto
        """

        return reverse(
            'product-detail',
            kwargs={
                'pk': obj.id,
                'organization_pk': obj.organization.id,
            },
            request=self.context['request'],
        )

    def get_repositories(self, obj: Product):
        """
        Retorna as URLS dos repositórios desse produto
        """
        repositories_urls = []

        for repository in obj.repositories.all():
            url = reverse(
                'repository-detail',
                kwargs={
                    'pk': repository.id,
                    'product_pk': obj.id,
                    'organization_pk': obj.organization.id,
                },
                request=self.context['request'],
            )
            repositories_urls.append(url)
        return repositories_urls

    def reverse_product_resource(self, obj: Product, viewname: str):
        return reverse(
            viewname,
            kwargs={
                'product_pk': obj.id,
                'organization_pk': obj.organization.id,
            },
            request=self.context['request'],
        )

    def get_actions(self, obj: Product):
        """
        Retorna o valor atuais das entidades associadas a um produto
        """
        create_a_new_repository_url = self.reverse_product_resource(
            obj, 'repository-list'
        )

        current_goal_url = self.reverse_product_resource(
            obj, 'current-goal-list'
        )

        compare_goals_url = self.reverse_product_resource(obj, 'all-goal-list')

        create_a_new_goal_url = self.reverse_product_resource(
            obj, 'create-goal-list'
        )

        current_release_config_url = self.reverse_product_resource(
            obj, 'current-release-config-list'
        )

        create_a_pre_config_url = self.reverse_product_resource(
            obj, 'create-release-config-list'
        )

        pre_config_entity_relationship_tree_url = (
            self.reverse_product_resource(
                obj, 'release-config-entity-relationship-tree-list'
            )
        )

        repositories_latest_tsqmis_url = self.reverse_product_resource(
            obj,
            'repositories-tsqmi-latest-values-list',
        )

        repositories_tsqmi_historical_values_url = (
            self.reverse_product_resource(
                obj,
                'repositories-tsqmi-historical-values-list',
            )
        )

        return {
            'create a new repository': create_a_new_repository_url,
            'get current goal': current_goal_url,
            'get compare all goals': compare_goals_url,
            'get current release-config': current_release_config_url,
            'get release-config entity relationship tree': pre_config_entity_relationship_tree_url,
            'get all repositories latest tsqmis': repositories_latest_tsqmis_url,
            'get all repositories tsqmi historical values': repositories_tsqmi_historical_values_url,
            'create a new goal': create_a_new_goal_url,
            'create a new release-config': create_a_pre_config_url,
        }


class RepositorySerializer(serializers.HyperlinkedModelSerializer):
    url = serializers.CharField(required=False, allow_blank=True)
    product = serializers.SerializerMethodField()
    latest_values = serializers.SerializerMethodField()
    historical_values = serializers.SerializerMethodField()
    actions = serializers.SerializerMethodField()

    class Meta:
        model = Repository
        fields = (
            'id',
            'url',
            'name',
            'description',
            'product',
            'latest_values',
            'historical_values',
            'actions',
            'platform',
            'imported'
        )
        extra_kwargs = {
            'key': {'read_only': True},
        }

    def validate(self, attrs):
        """
        Valida se o nome do repositório é único para o produto
        """
        name = attrs['name']
        product = self.context['view'].get_product()
        repository_id = self.instance.id if self.instance else None

        qs = Repository.objects.filter(name=name, product=product).exclude(
            id=repository_id
        )
        if qs.exists():
            raise serializers.ValidationError(
                'Repository with this name already exists.'
            )

        return attrs

    def validate_url(self, value):
        if value:
            parsed_url = urlparse(value)
            if parsed_url.scheme not in ['http', 'https']:
                raise serializers.ValidationError(
                    'The URL must start with http or https.'
                )

            try:
                response = requests.head(value, timeout=5)
                if response.status_code >= 400:
                    raise serializers.ValidationError(
                        "The repository's URL is not accessible."
                    )
            except RequestException:
                raise serializers.ValidationError(
                    "Unable to verify the repository's URL."
                )
        return value

    def get_url(self, obj: Repository):
        """
        Gera a URL desse repositório
        """

        return reverse(
            'repository-detail',
            kwargs={
                'pk': obj.id,
                'organization_pk': obj.product.organization.id,
                'product_pk': obj.product.id,
            },
            request=self.context['request'],
        )

    def get_product(self, obj: Repository):
        """
        Gera a URL do produto desse repositório
        """

        return reverse(
            'product-detail',
            kwargs={
                'pk': obj.product.id,
                'organization_pk': obj.product.organization.id,
            },
            request=self.context['request'],
        )

    def reverse_repository_resource(self, obj: Repository, viewname: str):
        return reverse(
            viewname,
            kwargs={
                'repository_pk': obj.id,
                'organization_pk': obj.product.organization.id,
                'product_pk': obj.product.id,
            },
            request=self.context['request'],
        )

    def get_actions(self, obj):
        # Lista todas as ações que podem ser feitas no repositório

        calculate_math_model_url = self.reverse_repository_resource(
            obj, 'math-model-list'
        )

        return {
            'calculate-math-model': calculate_math_model_url,
        }

    def get_historical_values(self, obj: Repository):
        """
        Gera a URL dos valores coletados históricos desse repositório
        """
        metrics_historical_values_url = self.reverse_repository_resource(
            obj,
            'metrics-historical-values-list',
        )

        measures_historical_values_url = self.reverse_repository_resource(
            obj,
            'measures-historical-values-list',
        )

        subcharacteristics_historical_values_url = (
            self.reverse_repository_resource(
                obj,
                'subcharacteristics-historical-values-list',
            )
        )

        characteristics_historical_values_url = (
            self.reverse_repository_resource(
                obj,
                'characteristics-historical-values-list',
            )
        )

        tsqmi_historical_values_url = self.reverse_repository_resource(
            obj,
            'tsqmi-historical-values-list',
        )

        return {
            'metrics': metrics_historical_values_url,
            'measures': measures_historical_values_url,
            'subcharacteristics': subcharacteristics_historical_values_url,
            'characteristics': characteristics_historical_values_url,
            'tsqmi': tsqmi_historical_values_url,
        }

    def get_latest_values(self, obj: Repository):
        """
        Gera a URL dos últimos valores coletados desse repositório
        """

        metrics_historical_values_url = self.reverse_repository_resource(
            obj, 'latest-collected-metrics-list'
        )

        measures_latest_values_url = self.reverse_repository_resource(
            obj,
            'latest-calculated-measures-list',
        )

        subcharacteristics_latest_values_url = (
            self.reverse_repository_resource(
                obj,
                'latest-calculated-subcharacteristics-list',
            )
        )

        characteristics_latest_values_url = self.reverse_repository_resource(
            obj,
            'latest-calculated-characteristics-list',
        )

        tsqmi_latest_values_url = self.reverse_repository_resource(
            obj,
            'latest-calculated-tsqmi-list',
        )

        return {
            'metrics': metrics_historical_values_url,
            'measures': measures_latest_values_url,
            'subcharacteristics': subcharacteristics_latest_values_url,
            'characteristics': characteristics_latest_values_url,
            'tsqmi': tsqmi_latest_values_url,
        }


class RepositoryTSQMILatestValueSerializer(serializers.ModelSerializer):
    """
    Serialização do último valor coletado de TSQMI
    """

    current_tsqmi = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()

    class Meta:
        model = Repository
        fields = ('id', 'url', 'name', 'current_tsqmi')

    def get_current_tsqmi(self, repository: Repository):
        tsqmi = repository.calculated_tsqmis.first()
        return TSQMISerializer(tsqmi).data if tsqmi else {}

    def get_url(self, obj: Repository):
        """
        Retorna a URL desse repositório com o último valor coletado de TSQMI
        """

        return reverse(
            'latest-calculated-tsqmi-list',
            kwargs={
                'repository_pk': obj.id,
                'organization_pk': obj.product.organization.id,
                'product_pk': obj.product.id,
            },
            request=self.context['request'],
        )


class RepositoriesTSQMIHistorySerializer(serializers.ModelSerializer):
    history = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()

    class Meta:
        model = Repository
        fields = ('id', 'url', 'name', 'history')

    def get_url(self, obj):
        """
        Retorna a URL desse produto
        """
        return reverse(
            'product-detail',
            kwargs={
                'pk': obj.id,
                'organization_pk': obj.product.organization.id,
            },
            request=self.context['request'],
        )

    def get_history(self, obj: Repository):
        MAX = settings.MAXIMUM_NUMBER_OF_HISTORICAL_RECORDS

        try:
            qs = obj.calculated_tsqmis.all().reverse()[:MAX]
            return TSQMISerializer(qs, many=True).data
        except TSQMI.DoesNotExist:
            return None
