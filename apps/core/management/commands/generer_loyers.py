"""
Management command pour générer automatiquement les appels de loyer mensuels.
Utilise bulk_create pour optimiser les performances.

Usage:
    python manage.py generer_loyers
    python manage.py generer_loyers --month 2025-06  # Pour un mois spécifique
    python manage.py generer_loyers --dry-run  # Simulation sans écriture
    Cette commande est pensée pour être planifiée via cron ou un scheduler (exemple)
    0 6 1 * * /path/to/venv/bin/python manage.py generer_loyers --verbosity 1
"""
import logging
from datetime import date
from dateutil.relativedelta import relativedelta
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from apps.core.models import Bail, Loyer

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Génère les appels de loyer mensuels pour tous les baux actifs (optimisé avec bulk_create)"

    def add_arguments(self, parser):
        """Options de ligne de commande."""
        parser.add_argument(
            '--month',
            type=str,
            help='Mois cible au format YYYY-MM (défaut: mois actuel)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simulation sans créer les loyers en base',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=500,
            help='Taille des lots pour bulk_create (défaut: 500)',
        )

    def handle(self, *args, **options):
        """Point d'entrée principal de la commande."""

        # ========================================
        # 1. DÉTERMINATION DE LA PÉRIODE
        # ========================================
        today = date.today()

        if options['month']:
            try:
                year, month = map(int, options['month'].split('-'))
                target_date = date(year, month, 1)
            except (ValueError, TypeError):
                raise CommandError(
                    "Format de mois invalide. Utilisez YYYY-MM (ex: 2025-06)"
                )
        else:
            target_date = today.replace(day=1)

        first_day = target_date
        last_day = first_day + relativedelta(months=1, days=-1)

        self.stdout.write(
            self.style.WARNING(
                f"\n{'=' * 60}\n"
                f"Génération des loyers pour : {first_day.strftime('%B %Y')}\n"
                f"Période : {first_day} → {last_day}\n"
                f"{'=' * 60}\n"
            )
        )

        # ========================================
        # 2. RÉCUPÉRATION DES BAUX ACTIFS
        # ========================================
        baux_actifs = Bail.objects.filter(
            est_signe=True,
            date_debut__lte=last_day,  # Bail commencé avant la fin du mois
            date_fin__gte=first_day  # Bail non terminé au début du mois
        ).select_related('locataire', 'bien')  # ✅ Optimisation N+1

        if not baux_actifs.exists():
            self.stdout.write(
                self.style.WARNING("⚠ Aucun bail actif trouvé pour cette période.")
            )
            self._actualiser_statuts_retard()
            return

        self.stdout.write(f"📋 {baux_actifs.count()} baux actifs détectés")

        # ========================================
        # 3. VÉRIFICATION DES LOYERS EXISTANTS
        # ========================================
        # ✅ Une seule requête pour tous les loyers du mois
        existing_bail_ids = set(
            Loyer.objects.filter(
                periode_debut=first_day
            ).values_list('bail_id', flat=True)
        )

        self.stdout.write(
            f"🔍 {len(existing_bail_ids)} loyers déjà générés pour ce mois"
        )

        # ========================================
        # 4. PRÉPARATION DES LOYERS À CRÉER
        # ========================================
        loyers_to_create = []
        baux_skipped = []

        for bail in baux_actifs:
            if bail.id in existing_bail_ids:
                baux_skipped.append(bail)
                continue

            # Calcul de la date d'échéance (sécurisé pour février)
            jour_paiement = min(bail.jour_paiement, last_day.day)
            date_echeance = first_day.replace(day=jour_paiement)

            # Création de l'objet Loyer (sans save)
            loyers_to_create.append(
                Loyer(
                    bail=bail,
                    periode_debut=first_day,
                    periode_fin=last_day,
                    date_echeance=date_echeance,
                    montant_du=bail.montant_loyer + bail.montant_charges,
                    montant_verse=0,
                    statut='A_PAYER'
                )
            )

        # ========================================
        # 5. MODE DRY-RUN
        # ========================================
        if options['dry_run']:
            self.stdout.write(
                self.style.WARNING(
                    f"\n🔍 MODE SIMULATION (--dry-run)\n"
                    f"   • {len(loyers_to_create)} loyers seraient créés\n"
                    f"   • {len(baux_skipped)} baux ignorés (déjà traités)\n"
                )
            )

            # Affichage détaillé en mode dry-run
            if loyers_to_create:
                self.stdout.write("\nAperçu des loyers à créer :")
                for loyer in loyers_to_create[:5]:  # 5 premiers
                    self.stdout.write(
                        f"  • {loyer.bail.locataire.get_full_name()} - "
                        f"{loyer.montant_du} FCFA (échéance: {loyer.date_echeance})"
                    )
                if len(loyers_to_create) > 5:
                    self.stdout.write(f"  ... et {len(loyers_to_create) - 5} autres")

            return

        # ========================================
        # 6. CRÉATION EN MASSE (BULK_CREATE)
        # ========================================
        if not loyers_to_create:
            self.stdout.write(
                self.style.SUCCESS(
                    "\n✓ Tous les loyers sont déjà générés pour ce mois."
                )
            )
            self._actualiser_statuts_retard()
            return

        try:
            with transaction.atomic():
                # ✅ Création en une seule requête SQL
                batch_size = options['batch_size']
                created_loyers = Loyer.objects.bulk_create(
                    loyers_to_create,
                    batch_size=batch_size
                )

                self.stdout.write(
                    self.style.SUCCESS(
                        f"\n✅ SUCCÈS : {len(created_loyers)} loyers créés avec succès\n"
                        f"   • Montant total généré : "
                        f"{sum(l.montant_du for l in loyers_to_create):,.0f} FCFA\n"
                        f"   • Baux traités : {len(loyers_to_create)}\n"
                        f"   • Baux ignorés : {len(baux_skipped)}\n"
                    )
                )

                # ========================================
                # 7. LOGGING DÉTAILLÉ
                # ========================================
                logger.info(
                    f"Génération loyers réussie - "
                    f"Période: {first_day} - "
                    f"Créés: {len(created_loyers)} - "
                    f"Ignorés: {len(baux_skipped)}"
                )

                # Log des baux traités pour audit
                for loyer in created_loyers:
                    logger.debug(
                        f"Loyer créé - Bail #{loyer.bail_id} - "
                        f"Locataire: {loyer.bail.locataire.username} - "
                        f"Montant: {loyer.montant_du} FCFA"
                    )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    f"\n❌ ERREUR lors de la création des loyers :\n{str(e)}"
                )
            )
            logger.error(
                f"Échec génération loyers - Période: {first_day} - "
                f"Erreur: {str(e)}",
                exc_info=True
            )
            raise

        # ========================================
        # 8. MISE À JOUR STATUTS RETARD & RÉSUMÉ FINAL
        # ========================================
        self.stdout.write(
            self.style.SUCCESS(
                f"\n{'=' * 60}\n"
                f"OPÉRATION TERMINÉE\n"
                f"{'=' * 60}\n"
            )
        )

    def _actualiser_statuts_retard(self):
        loyers_a_mettre_a_jour = Loyer.objects.filter(
            statut__in=["A_PAYER", "PARTIEL"],
        ).order_by("date_echeance")

        if not loyers_a_mettre_a_jour.exists():
            self.stdout.write("Aucun loyer à vérifier pour le statut RETARD.")
            return

        mis_a_jour = 0
        for loyer in loyers_a_mettre_a_jour:
            statut_initial = loyer.statut
            loyer.actualiser_statut_retard()
            if loyer.statut != statut_initial:
                mis_a_jour += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Statut RETARD mis à jour pour {mis_a_jour} loyers"
            )
        )