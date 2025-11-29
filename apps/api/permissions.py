from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import View

from apps.core.permissions import is_admin, is_locataire


class IsTenant(BasePermission):
    """
    Permission accordée aux locataires authentifiés et aux administrateurs.
    """

    message = "Accès réservé aux utilisateurs authentifiés."

    def has_permission(self, request: Request, view: View) -> bool:
        user = getattr(request, 'user', None)

        if not user or not user.is_authenticated:
            return False

        return is_admin(user) or is_locataire(user)