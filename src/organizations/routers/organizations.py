from organizations.routers.routers import Router
from organizations.views import ProductViewSet


class OrgRouter(Router):
    def __init__(self, parent_router, **children):
        super().__init__(
            parent_router,
            'organizations',
            'organization',
            children=[
                {
                    'name': 'products',
                    'view': ProductViewSet,
                    'basename': '',
                },
                *children,
            ],
        )
