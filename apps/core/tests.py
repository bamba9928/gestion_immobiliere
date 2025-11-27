from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

# Create your tests here.
from .models import Bail, Bien, EtatDesLieux


class EtatDesLieuxModelTests(TestCase):
    def test_str_returns_bail_identifier(self):
        user_model = get_user_model()
        proprietaire = user_model.objects.create_user(
            username="owner",
            email="owner@example.com",
            password="pass1234",
        )
        locataire = user_model.objects.create_user(
            username="tenant",
            email="tenant@example.com",
            password="pass1234",
        )

        bien = Bien.objects.create(
            titre="Appartement de test",
            adresse="1 rue de la Paix",
            ville="Dakar",
            surface=45,
            nb_pieces=2,
            description="",
            loyer_ref=Decimal("75000"),
            charges_ref=Decimal("5000"),
            proprietaire=proprietaire,
        )

        bail = Bail.objects.create(
            bien=bien,
            locataire=locataire,
            date_debut=date(2024, 1, 1),
            date_fin=date(2024, 12, 31),
            montant_loyer=Decimal("75000"),
            montant_charges=Decimal("5000"),
            depot_garantie=Decimal("150000"),
            jour_paiement=5,
            est_signe=True,
        )

        etat = EtatDesLieux.objects.create(
            bail=bail,
            type_edl="ENTREE",
            date_realisation=date(2024, 1, 1),
            checklist="",
        )

        self.assertEqual(str(etat), f"EDL Entrée - {bail.id}")