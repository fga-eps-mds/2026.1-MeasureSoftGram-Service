from django.conf import settings
import requests

from rest_framework import mixins, viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.authtoken.models import Token

from allauth.socialaccount.providers.github.views import GitHubOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client

from dj_rest_auth.registration.views import SocialLoginView

from accounts.models import CustomUser
from accounts.serializers import (
    APIAcessTokenRetrieveSerializer,
    AccountsCreateSerializer,
    AccountsLoginSerializer,
    AccountsRetrieveSerializer,
    GitHubAccessTokenRetrieveSerializer,
    UserListSerializer,
)


class GithubLoginViewSet(SocialLoginView):
    """
    ViewSet para login via OAuth2 do Github
    """

    adapter_class = GitHubOAuth2Adapter
    callback_url = settings.LOGIN_REDIRECT_URL
    client_class = OAuth2Client


class CreateAccountViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    """
    ViewSet para criação de conta
    """

    queryset = CustomUser.objects.all()
    serializer_class = AccountsCreateSerializer


class RetrieveAccountViewSet(
    mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    """
    ViewSet para recuperar informações de conta
    """

    permission_classes = (IsAuthenticated,)

    serializer_class = AccountsRetrieveSerializer

    def get_object(self):
        return self.request.user


class LoginViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    """
    ViewSet para login de conta
    """

    queryset = CustomUser.objects.all()
    serializer_class = AccountsLoginSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        return Response({'key': result.key}, status=status.HTTP_200_OK)


class LogoutViewSet(mixins.DestroyModelMixin, viewsets.GenericViewSet):
    """
    ViewSet para logout de conta
    """

    permission_classes = (IsAuthenticated,)

    def destroy(self, request, *args, **kwargs):
        return Response(status=status.HTTP_204_NO_CONTENT)


class RetrieveAPIAcessTokenViewSet(
    mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    """
    ViewSet para recuperar o token de acesso da conta do usuário, o token vai ser utilizado na github action
    """

    permission_classes = (IsAuthenticated,)

    serializer_class = APIAcessTokenRetrieveSerializer

    def get_object(self):
        user = CustomUser.objects.get(username=self.request.user)
        token = Token.objects.get(user=user)

        return token


class UserListViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para listar todos os usuários
    """

    queryset = CustomUser.objects.all()
    serializer_class = UserListSerializer


class UserRepos(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para os repositórios do github do user a partir de seu code
    """
    permission_classes = (IsAuthenticated,)

    serializer_class = GitHubAccessTokenRetrieveSerializer

    def retrieve(self, request):
        code = request.query_params.get('code')

        headers = {'Accept': 'application/json'}

        urlToken = 'https://github.com/login/oauth/access_token'
        data = {
            'client_id': settings.GITHUB_CLIENT_ID,
            'client_secret': settings.GITHUB_SECRET,
            'code': code,
            'redirect_uri': settings.LOGIN_REDIRECT_URL
        }
        response = requests.post(urlToken, data=data, headers=headers)
        token_data = response.json()
        if 'access_token' not in token_data:
            return Response(
                {"error": "Falha na autenticação do GitHub", "details": token_data}
                , status=status.HTTP_400_BAD_REQUEST)

        headersUser = {'Authorization': f'Bearer {token_data["access_token"]}'}
        urlRepos = 'https://api.github.com/user/repos?per_page=100'
        responseRepos = requests.get(urlRepos, headers=headersUser)
        repos_data = responseRepos.json()
        formatted_response = {
            "total_count": len(repos_data) if isinstance(repos_data, list) else 0,
            "items": repos_data if isinstance(repos_data, list) else []
        }

        return Response(formatted_response, status=status.HTTP_200_OK)


class GitHubOrganizationsViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
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
                return Response(
                    {"error": "GitHub account not linked or access token missing."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        headers = {"Authorization": f"token {token}", "Accept": "application/json"}
        results = []

        # 1. Fetch user's own profile (personal space)
        r_user = requests.get("https://api.github.com/user", headers=headers)
        if r_user.status_code == 200:
            user_data = r_user.json()
            results.append({
                "github_org_id": user_data.get("id"),
                "github_org_name": user_data.get("login"),
                "avatar_url": user_data.get("avatar_url"),
                "description": "Personal account",
            })

        # 2. Fetch user's organizations
        r_orgs = requests.get("https://api.github.com/user/orgs", headers=headers)
        if r_orgs.status_code == 200:
            orgs = r_orgs.json()
            for org in orgs:
                if any(x["github_org_id"] == org.get("id") for x in results):
                    continue
                results.append({
                    "github_org_id": org.get("id"),
                    "github_org_name": org.get("login"),
                    "avatar_url": org.get("avatar_url"),
                    "description": org.get("description"),
                })
        else:
            # If fetching orgs failed but user fetched successfully, return at least user
            if not results:
                return Response(
                    {"error": "Failed to fetch organizations from GitHub", "details": r_orgs.json()},
                    status=r_orgs.status_code
                )

        return Response(results, status=status.HTTP_200_OK)


