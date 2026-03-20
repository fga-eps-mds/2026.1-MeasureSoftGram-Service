from django.urls import include, re_path

from accounts.views import (
    GithubLoginViewSet,
    LogoutViewSet,
    CreateAccountViewSet,
    LoginViewSet,
    RetrieveAPIAcessTokenViewSet,
    RetrieveAccountViewSet,
    UserListViewSet,
    UserRepos
)

urlpatterns = [
    re_path(
        r'^accounts/',
        include(
            [
                re_path(
                    r'^signin/$',
                    CreateAccountViewSet.as_view({'post': 'create'}),
                    name='accounts-signin',
                ),
                re_path(
                    r'^login/$',
                    LoginViewSet.as_view({'post': 'create'}),
                    name='accounts-login',
                ),
                re_path(
                    r'^logout/$',
                    LogoutViewSet.as_view({'delete': 'destroy'}),
                    name='accounts-logout',
                ),
                re_path(
                    r'^$',
                    RetrieveAccountViewSet.as_view({'get': 'retrieve'}),
                    name='accounts-retrieve',
                ),
                re_path(
                    r'^github/login/$',
                    GithubLoginViewSet.as_view(),
                    name='github-login',
                ),
                re_path(
                    r'^access-token/$',
                    RetrieveAPIAcessTokenViewSet.as_view({'get': 'retrieve'}),
                    name='api-token-retrieve',
                ),
                re_path(
                    r'^users/$',
                    UserListViewSet.as_view({'get': 'list'}),
                    name='user-list',
                ),
                re_path(
                    r'^user-repos/$',
                    UserRepos.as_view({'get': 'retrieve'}),
                    name='user-repos',
                ),
            ]
        ),
    )
]
