import shutil
import tempfile
from datetime import date, timedelta
from decimal import Decimal

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.admin import CustomUserAdmin

# Create your tests here.
from .admin import BailAdmin
from .models import Bail, Bien, EtatDesLieux, Intervention, Loyer
from .protected_files import protected_url


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


# Plus petit GIF valide (1x1) : sert de photo d'intervention.
GIF = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,"
    b"\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
)


class FichiersPrivesTests(TestCase):
    """En production nginx ne sert que /media/biens/ : les autres fichiers doivent passer par des vues protégées."""

    @classmethod
    def setUpClass(cls):
        cls._media = tempfile.mkdtemp()
        cls._override = override_settings(MEDIA_ROOT=cls._media)
        cls._override.enable()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls._override.disable()
        shutil.rmtree(cls._media, ignore_errors=True)

    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.admin_user = user_model.objects.create_superuser("root", "root@example.com", "pass1234")
        cls.owner = user_model.objects.create_user("owner", "owner@example.com", "pass1234")
        cls.tenant = user_model.objects.create_user("tenant", "tenant@example.com", "pass1234")
        cls.stranger = user_model.objects.create_user("stranger", "stranger@example.com", "pass1234")
        Group.objects.get_or_create(name="BAILLEUR")[0].user_set.add(cls.owner)

        cls.bien = Bien.objects.create(
            titre="Appartement de test",
            adresse="1 rue de la Paix",
            ville="Dakar",
            surface=45,
            nb_pieces=2,
            description="",
            loyer_ref=Decimal("75000"),
            charges_ref=Decimal("5000"),
            proprietaire=cls.owner,
        )
        today = date.today()
        cls.bail = Bail.objects.create(
            bien=cls.bien,
            locataire=cls.tenant,
            date_debut=today - timedelta(days=30),
            date_fin=today + timedelta(days=300),
            montant_loyer=Decimal("75000"),
            montant_charges=Decimal("5000"),
            depot_garantie=Decimal("150000"),
            jour_paiement=5,
            est_signe=True,
            fichier_contrat=SimpleUploadedFile("contrat.pdf", b"%PDF-1.4 contrat", "application/pdf"),
        )
        cls.loyer = Loyer.objects.create(
            bail=cls.bail,
            periode_debut=today.replace(day=1),
            periode_fin=today.replace(day=28),
            date_echeance=today.replace(day=5),
            montant_du=Decimal("80000"),
            quittance=SimpleUploadedFile("quittance.pdf", b"%PDF-1.4 quittance", "application/pdf"),
        )
        cls.intervention = Intervention.objects.create(
            bien=cls.bien,
            locataire=cls.tenant,
            objet="Fuite d'eau",
            description="Fuite sous l'évier.",
            photo_avant=SimpleUploadedFile("avant.gif", GIF, "image/gif"),
        )

    def photo_url(self, phase="avant"):
        return reverse("download_intervention_photo", args=[self.intervention.pk, phase])

    # --- vue protégée des photos d'intervention -------------------------------------------------------------

    def test_photo_servie_a_l_admin_au_bailleur_et_au_locataire_auteur(self):
        for user in (self.admin_user, self.owner, self.tenant):
            with self.subTest(user=user.username):
                self.client.force_login(user)
                response = self.client.get(self.photo_url())
                self.assertEqual(response.status_code, 200)
                self.assertEqual(b"".join(response.streaming_content), GIF)
                self.assertEqual(response["Content-Type"], "image/gif")

    def test_photo_refusee_a_un_tiers(self):
        self.client.force_login(self.stranger)
        self.assertEqual(self.client.get(self.photo_url()).status_code, 403)

    def test_photo_anonyme_renvoyee_vers_la_connexion(self):
        response = self.client.get(self.photo_url())
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response["Location"])

    def test_photo_absente_ou_phase_inconnue(self):
        self.client.force_login(self.admin_user)
        self.assertEqual(self.client.get(self.photo_url("apres")).status_code, 404)  # pas de photo « après »
        self.assertEqual(self.client.get(self.photo_url("autre")).status_code, 404)

    def test_liste_des_interventions_utilise_la_vue_protegee(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse("interventions_list"))
        self.assertContains(response, self.photo_url())
        self.assertNotContains(response, "/media/interventions/")

    # --- liens de l'administration ----------------------------------------------------------------------------

    def test_protected_url(self):
        self.assertEqual(protected_url(self.bail.fichier_contrat), reverse("download_contrat", args=[self.bail.pk]))
        self.assertEqual(protected_url(self.loyer.quittance), reverse("download_quittance", args=[self.loyer.pk]))
        self.assertIsNone(protected_url(self.intervention.photo_avant))  # pas de vue dédiée mappée pour ce champ
        self.assertIsNone(protected_url(Bail().fichier_contrat))  # fichier vide : pas de lien

    def test_admin_du_bail_pointe_vers_la_vue_protegee(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse("admin:core_bail_change", args=[self.bail.pk]))
        self.assertContains(response, reverse("download_contrat", args=[self.bail.pk]))
        self.assertNotContains(response, "/media/baux_signes/")

    def test_admin_du_loyer_pointe_vers_la_vue_protegee(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse("admin:core_loyer_change", args=[self.loyer.pk]))
        self.assertContains(response, reverse("download_quittance", args=[self.loyer.pk]))
        self.assertNotContains(response, "/media/quittances/")

    def test_pieces_du_locataire_dans_l_admin_passent_par_la_vue_protegee(self):
        profile = self.tenant.profile
        profile.cni_scan = SimpleUploadedFile("cni.pdf", b"%PDF-1.4 cni", "application/pdf")
        profile.justificatif_domicile = SimpleUploadedFile("domicile.pdf", b"%PDF-1.4 dom", "application/pdf")
        profile.save()

        html = str(BailAdmin(Bail, admin.site).pieces_locataire(self.bail))
        self.assertIn(reverse("download_kyc", args=[self.tenant.pk, "cni"]), html)
        self.assertIn(reverse("download_kyc", args=[self.tenant.pk, "justificatif"]), html)
        self.assertNotIn("/media/", html)

    def test_lien_justificatif_domicile_de_l_admin_utilisateur(self):
        profile = self.tenant.profile
        profile.justificatif_domicile = SimpleUploadedFile("domicile.pdf", b"%PDF-1.4 dom", "application/pdf")
        profile.save()

        user_admin = CustomUserAdmin(type(self.tenant), admin.site)
        html = str(user_admin.justificatif_domicile_link(self.tenant))
        self.assertIn(reverse("download_kyc", args=[self.tenant.pk, "justificatif"]), html)
        self.assertNotIn("/media/", html)
