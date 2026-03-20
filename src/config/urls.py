from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from rest_framework_nested import routers
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions

from accounts import urls as accounts_urls
from characteristics.views import (
    BalanceMatrixViewSet,
    SupportedCharacteristicModelViewSet,
)
from entity_trees.views import SupportedEntitiesRelationshipTreeViewSet
from measures.views import SupportedMeasureModelViewSet
from metrics.views import SupportedMetricModelViewSet
from organizations.routers.organizations import OrgRouter
from organizations.routers.products import ProductRouter
from organizations.routers.repos import RepoRouter
from organizations.views import OrganizationViewSet
from subcharacteristics.views import SupportedSubCharacteristicModelViewSet


def register_supported_entities_endpoints(router):
    router.register('supported-metrics', SupportedMetricModelViewSet)
    router.register('supported-measures', SupportedMeasureModelViewSet)
    router.register(
        'supported-subcharacteristics', SupportedSubCharacteristicModelViewSet
    )
    router.register(
        'supported-characteristics', SupportedCharacteristicModelViewSet
    )
    router.register(
        'entity-relationship-tree',
        SupportedEntitiesRelationshipTreeViewSet,
        basename='entity-relationship-tree',
    )
    router.register(
        'balance-matrix',
        BalanceMatrixViewSet,
        basename='balance-matrix',
    )


main_router = routers.DefaultRouter()
register_supported_entities_endpoints(main_router)
main_router.register('organizations', OrganizationViewSet)


org_router = OrgRouter(main_router)


prod_router = ProductRouter(org_router.nested_router)


repo_router = RepoRouter(prod_router.nested_router)


schema_view = get_schema_view(
    openapi.Info(
        title="MeasureSoftGram API",
        default_version='v1',
        description="Swagger dos endpoints da API do measuresoftgram"
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include(main_router.urls)),
    path('api/v1/', include(org_router.nested_router.urls)),
    path('api/v1/', include(prod_router.nested_router.urls)),
    path('api/v1/', include(repo_router.nested_router.urls)),
    path('api/v1/', include(accounts_urls.urlpatterns)),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
]


if settings.DEBUG:
    urlpatterns.append(path('__debug__/', include('debug_toolbar.urls')))
