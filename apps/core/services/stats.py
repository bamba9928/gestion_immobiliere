from datetime import date

from django.db.models import Sum

from apps.core.models import Bien, Loyer


class DashboardService:
    def get_admin_stats(self):
        total_biens = Bien.objects.count()
        biens_occupes = Bien.objects.filter(
            baux__est_signe=True,
            baux__date_fin__gte=date.today(),
        ).distinct().count()

        impayes = Loyer.objects.filter(statut='RETARD').aggregate(
            total=Sum('montant_du')
        )['total'] or 0

        return {
            'total_biens': total_biens,
            'biens_occupes': biens_occupes,
            'taux_occupation': int((biens_occupes / total_biens) * 100) if total_biens > 0 else 0,
            'montant_impayes': impayes
        }

    def get_bailleur_stats(self, user):
        """
        Statistiques filtrées pour le bailleur connecté.
        Il ne voit que les données liées à SES biens.
        """
        # 1. Ses biens
        mes_biens = Bien.objects.filter(proprietaire=user)
        total_biens = mes_biens.count()

        # 2. Ses biens occupés (Bail signé + date valide)
        biens_occupes = mes_biens.filter(
            baux__est_signe=True,
            baux__date_fin__gte=date.today(),
        ).distinct().count()

        # 3. Ses impayés (Loyers en retard sur ses biens)
        impayes = Loyer.objects.filter(
            bail__bien__in=mes_biens,
            statut='RETARD'
        ).aggregate(total=Sum('montant_du'))['total'] or 0

        # 4. Calcul Taux
        taux = int((biens_occupes / total_biens) * 100) if total_biens > 0 else 0

        return {
            'total_biens': total_biens,
            'biens_occupes': biens_occupes,
            'taux_occupation': taux,
            'montant_impayes': impayes
        }