"""
Permissões customizadas para controle de acesso aos dashboards.
"""
import logging

from rest_framework import permissions

from organizations.models import Repository

logger = logging.getLogger(__name__)


class HasRepositoryAccess(permissions.BasePermission):
    """
    Permissão que verifica se o usuário tem acesso ao repositório
    através da cadeia: User → Organization → Product → Repository
    """

    def has_permission(self, request, view):
        """
        Verifica se o usuário está autenticado.
        """
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        """
        Verifica se o usuário tem acesso ao objeto (Repository).
        """
        if isinstance(obj, Repository):
            return self._user_can_access_repository(request.user, obj)
        return False

    def _user_can_access_repository(self, user, repository: Repository) -> bool:
        """
        Verifica se o usuário tem acesso ao repositório através de:
        User → Organization → Product → Repository

        Args:
            user: Usuário autenticado
            repository: Repositório a ser acessado

        Returns:
            bool: True se o usuário tem acesso
        """
        # Administradores têm acesso total
        if user.is_staff or user.is_superuser:
            return True

        # Verifica se o repositório pertence a uma organização administrada pelo usuário
        return Repository.objects.filter(
            id=repository.id, product__organization__admin=user  # Admin da organização
        ).exists()


class CanAccessDashboard(permissions.BasePermission):
    """
    Permissão genérica para acesso a dashboards.
    Valida repository_id se presente nos query params.
    """

    def has_permission(self, request, view):
        """
        Valida acesso ao dashboard com base nos parâmetros da requisição.
        """
        if not request.user or not request.user.is_authenticated:
            return False

        repository_id = request.query_params.get('repository_id')

        # Se não há repository_id, permite (dashboards gerais)
        if not repository_id:
            return True

        # Se há repository_id, valida acesso
        try:
            repository = Repository.objects.get(id=repository_id)
            return HasRepositoryAccess()._user_can_access_repository(request.user, repository)
        except Repository.DoesNotExist:
            logger.warning(f'Repository {repository_id} não encontrado')
            return False
        except ValueError:
            logger.warning(f'repository_id inválido: {repository_id}')
            return False
