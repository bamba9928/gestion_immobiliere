from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from .models import Annonce, Bail

@receiver(post_save, sender=Bail)
def archive_annonces_on_signed_bail(sender, instance: Bail, **kwargs):
    """
    Archive les annonces liées au bien dès que le bail est signé.
    """
    if instance.est_signe:
        # On utilise update() pour une requête SQL unique et rapide
        Annonce.objects.filter(
            bien=instance.bien,
            statut="PUBLIE"
        ).update(
            statut="ARCHIVE",
            updated_at=timezone.now()
        )