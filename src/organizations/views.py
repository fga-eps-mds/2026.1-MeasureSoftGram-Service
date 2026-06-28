from rest_framework import mixins, permissions, viewsets, status
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from drf_yasg.utils import swagger_auto_schema
import requests

from organizations.models import Organization, Product, Repository
from organizations.mixins import UserScopedMixin
from organizations.serializers import (
    OrganizationSerializer,
    ProductSerializer,
    RepositoriesTSQMIHistorySerializer,
    RepositorySerializer,
    RepositoryTSQMILatestValueSerializer,
)


class OrganizationViewSet(UserScopedMixin, viewsets.ModelViewSet):
    queryset = (
        Organization.objects.all().order_by('id').prefetch_related('products')
    )
    serializer_class = OrganizationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.get_user_organizations().order_by('id').prefetch_related('products')

    def perform_create(self, serializer):
        org = serializer.save(admin=self.request.user)
        org.members.add(self.request.user)


class ProductViewSet(UserScopedMixin, viewsets.ModelViewSet):
    queryset = (
        Product.objects.all()
        .order_by('-id')
        .select_related('organization')
        .prefetch_related('repositories')
    )
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        org = self.get_organization()
        qs = (
            Product.objects.all()
            .order_by('-id')
            .select_related('organization')
            .prefetch_related('repositories')
        )
        return qs.filter(organization=org)

    def perform_create(self, serializer):
        org = self.get_organization()
        serializer.save(organization=org)


class RepositoryViewSetMixin(UserScopedMixin):
    permission_classes = [permissions.IsAuthenticated]


class RepositoryViewSet(
    RepositoryViewSetMixin,
    viewsets.ModelViewSet,
):
    serializer_class = RepositorySerializer
    queryset = Repository.objects.all()

    def perform_create(self, serializer):
        serializer.is_valid(raise_exception=True)
        product = self.get_product()
        repository = serializer.save(product=product)

        # Trigger background onboarding if not running unit tests
        from django.conf import settings
        if not getattr(settings, 'TESTING', False):
            import threading
            from organizations.utils import onboard_repository_async
            thread = threading.Thread(
                target=onboard_repository_async,
                args=(repository, self.request.user),
                daemon=True
            )
            thread.start()

    def get_queryset(self):
        product = self.get_product()
        qs = Repository.objects.all().order_by('-id').select_related('product')
        return qs.filter(product=product)


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


class ImportOrganizationViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request):
        github_org_name = request.data.get("github_org_name")
        if not github_org_name:
            return Response({"error": "github_org_name is required."}, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        token = user.github_access_token
        if not token:
            from allauth.socialaccount.models import SocialToken
            st = SocialToken.objects.filter(account__user=user, account__provider='github').first()
            if st:
                token = st.token
                user.github_access_token = token
                user.save()
            else:
                return Response({"error": "GitHub account not linked."}, status=status.HTTP_400_BAD_REQUEST)

        is_personal = (github_org_name.lower() == user.username.lower())
        headers = {"Authorization": f"token {token}", "Accept": "application/json"}

        if is_personal:
            url_fetch = "https://api.github.com/user"
        else:
            url_fetch = f"https://api.github.com/orgs/{github_org_name}"

        r = requests.get(url_fetch, headers=headers)
        if r.status_code != 200:
            return Response(
                {"error": "Failed to fetch metadata from GitHub", "details": r.json()},
                status=r.status_code
            )

        org_data = r.json()
        github_org_id = org_data.get("id")

        if not is_personal:
            r_member = requests.get(
                f"https://api.github.com/user/memberships/orgs/{github_org_name}",
                headers=headers
            )
            if r_member.status_code != 200:
                return Response(
                    {"error": f"User is not a member of organization '{github_org_name}' in GitHub."},
                    status=status.HTTP_403_FORBIDDEN
                )

        org, created = Organization.objects.get_or_create(
            github_org_id=github_org_id,
            defaults={
                "name": org_data.get("name") or org_data.get("login") or github_org_name,
                "github_org_name": github_org_name,
                "avatar_url": org_data.get("avatar_url"),
                "description": org_data.get("bio") if is_personal else org_data.get("description"),
            }
        )
        if not created:
            org.name = org_data.get("name") or org_data.get("login") or github_org_name
            org.github_org_name = github_org_name
            org.avatar_url = org_data.get("avatar_url")
            org.description = org_data.get("bio") if is_personal else org_data.get("description")
            org.save()

        org.members.add(user)
        if not org.admin:
            org.admin = user
            org.save()

        from organizations.serializers import OrganizationSerializer
        serializer = OrganizationSerializer(org, context={"request": request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class GitHubReposViewSet(UserScopedMixin, viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request, organization_pk=None):
        org = self.get_organization()
        github_org_name = org.github_org_name
        if not github_org_name:
            return Response({"error": "Organization is not linked to GitHub."}, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        token = user.github_access_token
        if not token:
            from allauth.socialaccount.models import SocialToken
            st = SocialToken.objects.filter(account__user=user, account__provider='github').first()
            if st:
                token = st.token
                user.github_access_token = token
                user.save()
            else:
                return Response({"error": "GitHub account not linked."}, status=status.HTTP_400_BAD_REQUEST)

        is_personal = (github_org_name.lower() == user.username.lower())
        headers = {"Authorization": f"token {token}", "Accept": "application/json"}

        if is_personal:
            url_fetch = "https://api.github.com/user/repos?affiliation=owner&per_page=100"
        else:
            url_fetch = f"https://api.github.com/orgs/{github_org_name}/repos?per_page=100"

        r = requests.get(url_fetch, headers=headers)
        if r.status_code != 200:
            return Response(
                {"error": f"Failed to fetch repositories for '{github_org_name}'", "details": r.json()},
                status=r.status_code
            )

        repos = r.json()
        results = []
        for repo in repos:
            results.append({
                "github_repo_id": repo.get("id"),
                "github_full_name": repo.get("full_name"),
                "name": repo.get("name"),
                "description": repo.get("description"),
                "url": repo.get("html_url"),
            })
        return Response(results, status=status.HTTP_200_OK)
