import logging

from ..models import Transaction

logger = logging.getLogger(__name__)


class PaymentService:
    def initier_paiement(self, loyer, provider, telephone):
        """
        Simule l'appel à l'API Wave ou Orange Money.
        """
        # Créer une transaction en attente
        transaction = Transaction.objects.create(
            loyer=loyer,
            montant=loyer.reste_a_payer,
            provider=provider
        )

        # ICI : Code pour appeler l'API réelle (ex: requests.post...)
        logger.info(f"Demande de paiement envoyée à {provider} pour {telephone}")

        # Pour le prototype, on simule une URL de redirection
        return transaction, "https://wave.com/checkout/simule"

    def confirmer_paiement(self, transaction_id, reference_externe):
        """
        Webhook ou callback pour valider le paiement
        """
        try:
            tx = Transaction.objects.get(id=transaction_id)
            tx.est_validee = True
            tx.reference_externe = reference_externe
            tx.save()

            # Mettre à jour le loyer
            tx.loyer.enregistrer_paiement(tx.montant)
            return True
        except Transaction.DoesNotExist:
            return False

class PaymentService:
    def creer_transaction(self, loyer, provider):
        """
        Crée une transaction initiale en attente.
        """
        transaction = Transaction.objects.create(
            loyer=loyer,
            montant=loyer.reste_a_payer,
            provider=provider,
            est_validee=False
        )
        return transaction

    def valider_transaction(self, transaction_id):
        """
        Valide la transaction et met à jour le loyer.
        Simule le callback (webhook) de l'opérateur.
        """
        try:
            tx = Transaction.objects.get(id=transaction_id)
            if tx.est_validee:
                return False  # Déjà validée

            # 1. Marquer la transaction comme validée
            tx.est_validee = True
            # Générer une fausse référence opérateur (ex: WAV-12345...)
            tx.reference_externe = f"{tx.provider}-{str(uuid.uuid4())[:8].upper()}"
            tx.save()

            # 2. Mettre à jour le loyer (déclenche la génération de quittance via le modèle Loyer)
            tx.loyer.enregistrer_paiement(tx.montant)

            return True
        except Transaction.DoesNotExist:
            return False