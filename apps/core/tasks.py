from celery import shared_task
from django.core.management import call_command
from django.core.mail import send_mail
from django.utils import timezone
from datetime import timedelta
from .models import Loyer

@shared_task
def generer_loyers_task():
    call_command("generer_loyers")
@shared_task
def envoyer_relances_paiement():
    today = timezone.now().date()
    # Loyers en retard de plus de 5 jours sans relance récente
    loyers_retard = Loyer.objects.filter(
        statut='RETARD',
        date_echeance__lte=today - timedelta(days=5)
    )

    for loyer in loyers_retard:
        # Logique d'envoi d'email
        send_mail(
            f"Relance : Loyer impayé - {loyer.periode_debut.strftime('%B %Y')}",
            f"Bonjour {loyer.bail.locataire.first_name}, sauf erreur de notre part...",
            "no-reply@mada-immo.sn",
            [loyer.bail.locataire.email]
        )
        # Enregistrer l'action (nécessite un nouveau modèle HistoriqueRelance si on veut être strict)
