import uuid
from django.db import transaction
from django.utils import timezone
from ..models import Transaction


class PaymentService:
    def enregistrer_paiement_especes(self, loyer, montant, auteur_admin=None):
        """
        Enregistre un paiement manuel en CASH :
        1. Crée une Transaction validée (pour la comptabilité).
        2. Met à jour le Loyer (montant versé, statut, quittance).
        """
        if montant <= 0:
            raise ValueError("Le montant doit être positif.")

        if montant > loyer.reste_a_payer:
            raise ValueError(f"Le montant ({montant}) dépasse le reste à payer ({loyer.reste_a_payer}).")

        with transaction.atomic():
            # 1. Création de la trace comptable (Transaction)
            # Génération d'une référence unique interne
            ref = f"CASH-{timezone.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:4].upper()}"

            Transaction.objects.create(
                loyer=loyer,
                montant=montant,
                provider="CASH",  # On force le type CASH
                type_flux="LOYER",
                est_validee=True,  # Validé d'office car reçu en main propre
                reference_externe=ref
            )

            # 2. Mise à jour du loyer (Ceci déclenche la logique métier et la quittance)
            loyer.enregistrer_paiement(montant)