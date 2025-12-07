from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from .models import Annonce, Bail

@receiver(post_save, sender=Bail)
def archive_annonces_on_signed_bail(sender, instance: Bail, created=False, update_fields=None, **kwargs):
    # Rien à faire si non signé
    if not instance.est_signe:
        return

    # Si update_fields est renseigné et ne contient pas est_signe → inutile de continuer
    if update_fields is not None and "est_signe" not in update_fields and not created:
        return

    Annonce.objects.filter(
        bien=instance.bien,
        statut="PUBLIE"
    ).update(
        statut="ARCHIVE",
        updated_at=timezone.now()
    )
