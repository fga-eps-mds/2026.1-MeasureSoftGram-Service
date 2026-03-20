from organizations.models import Repository, Product
from rest_framework.generics import get_object_or_404


def get_repository(organization_id, product_id, repository_id):
    return get_object_or_404(
        Repository,
        id=repository_id,
        product_id=product_id,
        product__organization_id=organization_id,
    )


def get_product(organization_id, product_id):
    return get_object_or_404(
        Product,
        id=product_id,
        organization_id=organization_id,
    )
