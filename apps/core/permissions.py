from django.contrib.auth.models import Group

def user_in_group(user, group_name: str) -> bool:
    return user.is_authenticated and user.groups.filter(name=group_name).exists()

def is_admin(user) -> bool:
    return user.is_superuser or user_in_group(user, 'ADMIN')

def is_bailleur(user) -> bool:
    return user_in_group(user, 'BAILLEUR')

def is_locataire(user) -> bool:
    return user_in_group(user, 'LOCATAIRE')

def is_agent(user) -> bool:
    return user_in_group(user, 'AGENT')
