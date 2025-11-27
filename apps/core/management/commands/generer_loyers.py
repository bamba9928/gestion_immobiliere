import logging
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.core.models import Bail, Loyer

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Génère les appels de loyer pour le mois en cours pour tous les baux actifs."

    def handle(self, *args, **options):
        today = date.today()
        first_day_of_month = today.replace(day=1)
        last_day_of_month = first_day_of_month + relativedelta(months=1, days=-1)

        self.stdout.write(
            f"--- Génération des loyers pour la période : {first_day_of_month} au {last_day_of_month} ---")

        # 1. Récupérer les baux actifs qui couvrent la période actuelle
        baux_actifs = Bail.objects.filter(
            est_signe=True,
            date_debut__lte=last_day_of_month,  # Le bail doit avoir commencé
            date_fin__gte=first_day_of_month  # Le bail ne doit pas être fini avant le début du mois
        )

        compteur_crees = 0
        compteur_existants = 0

        for bail in baux_actifs:
            try:
                with transaction.atomic():
                    # 2. Vérifier si un loyer existe déjà pour ce bail et ce mois
                    loyer_exists = Loyer.objects.filter(
                        bail=bail,
                        periode_debut=first_day_of_month
                    ).exists()

                    if loyer_exists:
                        compteur_existants += 1
                        continue

                    # 3. Calcul de la date d'échéance (ex: le 5 du mois)
                    jour_paiement = min(bail.jour_paiement, 28)  # Sécurité pour février
                    date_echeance = first_day_of_month.replace(day=jour_paiement)

                    # 4. Création du loyer
                    montant_total = bail.montant_loyer + bail.montant_charges

                    Loyer.objects.create(
                        bail=bail,
                        periode_debut=first_day_of_month,
                        periode_fin=last_day_of_month,
                        date_echeance=date_echeance,
                        montant_du=montant_total,
                        montant_verse=0,
                        statut='A_PAYER'
                    )

                    compteur_crees += 1
                    self.stdout.write(self.style.SUCCESS(f"✓ Loyer créé pour {bail}"))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"x Erreur pour le bail {bail.id}: {str(e)}"))

        self.stdout.write(
            self.style.SUCCESS(f"--- Terminé : {compteur_crees} créés, {compteur_existants} déjà existants ---"))