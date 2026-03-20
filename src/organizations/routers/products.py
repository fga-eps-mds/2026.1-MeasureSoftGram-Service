from entity_trees.views import ReleaseConfigurationEntitiesRelationshipTreeViewSet
from goals.views import (
    CompareGoalsModelViewSet,
    CreateGoalModelViewSet,
    CurrentGoalModelViewSet
)
from organizations.routers.routers import Router
from organizations.views import (
    RepositoriesTSQMIHistoryViewSet,
    RepositoriesTSQMILatestValueViewSet,
    RepositoryViewSet,
)
from release_configuration.views import (
    CreateReleaseConfigModelViewSet,
    CurrentReleaseConfigModelViewSet,
    DefaultPreConfigModelViewSet,
)
from releases.views import ReleaseModelViewSet


class ProductRouter(Router):
    def __init__(self, parent_router, **children):
        super().__init__(
            parent_router,
            'products',
            'product',
            children=[
                {
                    'name': 'entity-relationship-tree',
                    'view': ReleaseConfigurationEntitiesRelationshipTreeViewSet,
                    'basename': 'release-config-entity-relationship-tree',
                },
                {
                    'name': 'repositories-tsqmi-latest-values',
                    'view': RepositoriesTSQMILatestValueViewSet,
                    'basename': 'repositories-tsqmi-latest-values',
                },
                {
                    'name': 'repositories-tsqmi-historical-values',
                    'view': RepositoriesTSQMIHistoryViewSet,
                    'basename': 'repositories-tsqmi-historical-values',
                },
                {
                    'name': 'repositories',
                    'view': RepositoryViewSet,
                    'basename': '',
                },
                *self._get_goals_endpoints_dicts(),
                *self._get_ReleaseConfigurations_endpoints_dict(),
                *children,
            ],
        )

    def _get_goals_endpoints_dicts(self):
        return [
            {
                'name': 'current/goal',
                'view': CurrentGoalModelViewSet,
                'basename': 'current-goal',
            },
            {
                'name': 'create/goal',
                'view': CreateGoalModelViewSet,
                'basename': 'create-goal',
            },
            {
                'name': 'all/goal',
                'view': CompareGoalsModelViewSet,
                'basename': 'all-goal',
            },
            {
                'name': 'release',
                'view': ReleaseModelViewSet,
                'basename': 'create-release',
            }
        ]

    def _get_ReleaseConfigurations_endpoints_dict(self):
        return [
            {
                'name': 'current/release-config',
                'view': CurrentReleaseConfigModelViewSet,
                'basename': 'current-release-config',
            },
            {
                'name': 'default/pre-config',
                'view': DefaultPreConfigModelViewSet,
                'basename': 'default-pre-config',
            },
            {
                'name': 'create/release-config',
                'view': CreateReleaseConfigModelViewSet,
                'basename': 'create-release-config',
            },
        ]
