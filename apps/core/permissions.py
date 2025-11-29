# permissions.py
from datetime import date
from django.contrib.auth.models import Group
from .models import Bail  # importe ton modèle

def user_in_group(user, group_name: str) -> bool:
    return user.is_authenticated and user.groups.filter(name=group_name).exists()


def is_admin(user) -> bool:
    return user.is_superuser or user_in_group(user, "ADMIN")


def is_bailleur(user) -> bool:
    return user_in_group(user, "BAILLEUR")


def is_locataire(user) -> bool:
    return user_in_group(user, "LOCATAIRE")


def is_agent(user) -> bool:
    return user_in_group(user, "AGENT")


def get_active_bail(user):
    """
    Retourne le bail actif du locataire connecté :
    - bail signé
    - date_debut <= aujourd'hui <= date_fin
    - le locataire est l'utilisateur
    """
    if not user.is_authenticated:
        return None

    today = date.today()

    return (
        Bail.objects.filter(
            locataire=user,
            est_signe=True,
            date_debut__lte=today,
            date_fin__gte=today,
        )
        .order_by("-date_debut")
        .first()
    )
