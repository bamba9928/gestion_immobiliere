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
        biens = Bien.objects.filter(proprietaire=user)

        return {}  # Remplir avec la logique extraite