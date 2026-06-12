from rest_framework.generics import get_object_or_404
from rest_framework.exceptions import PermissionDenied
from organizations.models import Organization, Product, Repository

class UserScopedMixin:
    """
    Mixin to enforce that querysets and objects are restricted to organizations
    where request.user is a member.
    """
    def get_user_organizations(self):
        return Organization.objects.filter(members=self.request.user)

    def get_user_products(self):
        return Product.objects.filter(organization__members=self.request.user)

    def get_user_repositories(self):
        return Repository.objects.filter(product__organization__members=self.request.user)

    def get_organization(self):
        org_pk = self.kwargs.get('organization_pk') or self.kwargs.get('pk')
        return get_object_or_404(
            self.get_user_organizations(),
            id=org_pk
        )

    def get_product(self):
        org_pk = self.kwargs.get('organization_pk')
        prod_pk = self.kwargs.get('product_pk') or self.kwargs.get('pk')
        return get_object_or_404(
            self.get_user_products().filter(organization_id=org_pk),
            id=prod_pk
        )

    def get_repository(self):
        org_pk = self.kwargs.get('organization_pk')
        prod_pk = self.kwargs.get('product_pk')
        repo_pk = self.kwargs.get('repository_pk') or self.kwargs.get('pk')
        return get_object_or_404(
            self.get_user_repositories().filter(
                product_id=prod_pk,
                product__organization_id=org_pk
            ),
            id=repo_pk
        )

