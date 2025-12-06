from datetime import timedelta
import logging

from celery import shared_task
from django.conf import settings
from django.core.management import call_command
from django.core.mail import send_mail
from django.utils import timezone

from .models import Loyer, HistoriqueRelance

logger = logging.getLogger(__name__)


@shared_task
def generer_loyers_task():
    """Tâche Celery pour lancer la commande de génération des loyers."""
    try:
        call_command("generer_loyers")
        logger.info("Commande 'generer_loyers' exécutée avec succès.")
    except Exception as exc:
        logger.exception("Erreur lors de l'exécution de 'generer_loyers': %s", exc)
        raise


@shared_task
def envoyer_relances_paiement():
    """
    Envoie des relances pour les loyers en retard depuis au moins 5 jours,
    sans relance récente (ex. < 5 jours).
    """
    today = timezone.localdate()
    DELAI_RETARD_JOURS = 5
    DELAI_RELANCE_JOURS = 5

    loyers_retard = (
        Loyer.objects
        .select_related("bail__locataire")
        .filter(
            statut="RETARD",
            date_echeance__lte=today - timedelta(days=DELAI_RETARD_JOURS),
        )
    )

    for loyer in loyers_retard:
        locataire = loyer.bail.locataire

        # 1) Vérifier qu'on a un email
        if not locataire.email:
            logger.warning(
                "Impossible d'envoyer une relance pour le loyer %s : locataire sans email.",
                loyer.pk,
            )
            continue

        # 2) Vérifier la dernière relance envoyée pour ce loyer
        derniere_relance = loyer.relances.order_by("-date_envoi").first()
        if derniere_relance:
            limite = timezone.now() - timedelta(days=DELAI_RELANCE_JOURS)
            if derniere_relance.date_envoi >= limite:
                # Une relance récente existe déjà, on ne renvoie pas
                logger.info(
                    "Relance déjà envoyée récemment pour le loyer %s, on saute.",
                    loyer.pk,
                )
                continue

        # 3) Construire le mail
        subject = f"Relance : Loyer impayé - {loyer.periode_debut.strftime('%B %Y')}"
        body = (
            f"Bonjour {locataire.first_name or locataire.username},\n\n"
            "Sauf erreur de notre part, nous n'avons pas encore reçu le règlement de votre loyer.\n"
            f"Montant dû : {loyer.reste_a_payer} FCFA.\n\n"
            "Merci de procéder au paiement dans les meilleurs délais.\n\n"
            "Cordialement,\n"
            "MADA IMMO"
        )
        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@mada-immo.sn")

        # 4) Envoi + journalisation dans l'historique
        try:
            send_mail(
                subject,
                body,
                from_email,
                [locataire.email],
                fail_silently=False,
            )
            HistoriqueRelance.objects.create(
                loyer=loyer,
                canal="EMAIL",
                succes=True,
                message=body,
            )
            logger.info(
                "Relance envoyée pour le loyer %s (locataire %s).",
                loyer.pk,
                locataire.pk,
            )
        except Exception:
            HistoriqueRelance.objects.create(
                loyer=loyer,
                canal="EMAIL",
                succes=False,
                message="Erreur lors de l'envoi de l'email de relance.",
            )
            logger.exception(
                "Erreur lors de l'envoi de la relance pour le loyer %s.",
                loyer.pk,
            )
