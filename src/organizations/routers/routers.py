from rest_framework_nested import routers


class Router:
    def __init__(self, parent_router, name, lookup, **kwargs):
        self.nested_router = routers.NestedDefaultRouter(
            parent_router,
            name,
            lookup=lookup,
        )
        children = kwargs.pop('children')
        if children:
            for child in children:
                c_name = child.pop('name')
                c_view = child.pop('view')

                if c_name and c_view:
                    basename = child.pop('basename')
                    if basename:
                        self.nested_router.register(
                            c_name, c_view, basename=basename
                        )
                    else:
                        self.nested_router.register(c_name, c_view)
