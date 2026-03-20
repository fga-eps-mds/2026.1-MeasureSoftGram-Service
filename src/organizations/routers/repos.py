from characteristics.views import (
    CalculateCharacteristicViewSet,
    CalculatedCharacteristicHistoryModelViewSet,
    LatestCalculatedCharacteristicModelViewSet,
)
from math_model.views import CalculateMathModelViewSet
from measures.views import (
    CalculatedMeasureHistoryModelViewSet,
    CalculateMeasuresViewSet,
    LatestCalculatedMeasureModelViewSet,
)
from metrics.views import (
    CollectedMetricHistoryModelViewSet,
    LatestCollectedMetricModelViewSet,
)
from organizations.routers.routers import Router
from subcharacteristics.views import (
    CalculatedSubCharacteristicHistoryModelViewSet,
    LatestCalculatedSubCharacteristicModelViewSet,
)
from tsqmi.views import (
    CalculatedTSQMIHistoryModelViewSet,
    LatestCalculatedTSQMIBadgeViewSet,
    LatestCalculatedTSQMIViewSet,
)


class RepoRouter(Router):
    def __init__(self, parent_router, **children):
        super().__init__(
            parent_router,
            'repositories',
            'repository',
            children=[
                *self._get_actions_endpoints_dicts(),
                *self._get_latest_values_endpoints_dict(),
                *self._get_historic_values_endpoints_dicts(),
                *children,
            ],
        )

    def _get_actions_endpoints_dicts(self):
        return [
            {
                'name': 'calculate/math-model',
                'view': CalculateMathModelViewSet,
                'basename': 'math-model',
            },
        ]

    def _get_latest_values_endpoints_dict(self):
        return [
            {
                'name': 'latest-values/metrics',
                'view': LatestCollectedMetricModelViewSet,
                'basename': 'latest-collected-metrics',
            },
            {
                'name': 'latest-values/measures',
                'view': LatestCalculatedMeasureModelViewSet,
                'basename': 'latest-calculated-measures',
            },
            {
                'name': 'latest-values/subcharacteristics',
                'view': LatestCalculatedSubCharacteristicModelViewSet,
                'basename': 'latest-calculated-subcharacteristics',
            },
            {
                'name': 'latest-values/characteristics',
                'view': LatestCalculatedCharacteristicModelViewSet,
                'basename': 'latest-calculated-characteristics',
            },
            {
                'name': 'latest-values/tsqmi',
                'view': LatestCalculatedTSQMIViewSet,
                'basename': 'latest-calculated-tsqmi',
            },
            {
                "name": "latest-values/tsqmi/badge",
                "view": LatestCalculatedTSQMIBadgeViewSet,
                "basename": "latest-calculated-tsqmi-badge",
            },
        ]

    def _get_historic_values_endpoints_dicts(self):
        return [
            {
                'name': 'historical-values/metrics',
                'view': CollectedMetricHistoryModelViewSet,
                'basename': 'metrics-historical-values',
            },
            {
                'name': 'historical-values/measures',
                'view': CalculatedMeasureHistoryModelViewSet,
                'basename': 'measures-historical-values',
            },
            {
                'name': 'historical-values/subcharacteristics',
                'view': CalculatedSubCharacteristicHistoryModelViewSet,
                'basename': 'subcharacteristics-historical-values',
            },
            {
                'name': 'historical-values/characteristics',
                'view': CalculatedCharacteristicHistoryModelViewSet,
                'basename': 'characteristics-historical-values',
            },
            {
                'name': 'historical-values/tsqmi',
                'view': CalculatedTSQMIHistoryModelViewSet,
                'basename': 'tsqmi-historical-values',
            },
        ]
