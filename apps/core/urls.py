from django.contrib.auth import views as auth_views
from django.urls import path

from . import views
from .views import ContactView, add_locataire, add_bailleur, add_agent

urlpatterns = [
    # ============================================
    # PAGES PUBLIQUES (Non authentifiées)
    # ============================================
    path("", views.HomeView.as_view(), name="home"),  # Page d'accueil avec annonces
    path("about/", views.about, name="about"),
    path("annonce/<int:pk>/", views.AnnonceDetailView.as_view(), name="annonce_detail"),
    path("contact/", ContactView.as_view(), name="contact"),

    # ============================================
    # AUTHENTIFICATION
    # ============================================
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="registration/login.html",
            redirect_authenticated_user=True,
        ),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),

    # ============================================
    # TABLEAU DE BORD & GESTION (Protégé)
    # ============================================
    path("dashboard/", views.dashboard, name="dashboard"),
    path("dashboard/locataires/add/", add_locataire, name="add_locataire"),
    path("dashboard/bailleur/nouveau/", add_bailleur, name="add_bailleur"),
    path("dashboard/agent/nouveau/", add_agent, name="add_agent"),

    # Gestion des biens
    path("gestion/biens/add/", views.add_bien, name="add_bien"),
    path('annonces/<int:pk>-<str:slug>/', views.AnnonceDetailView.as_view(), name='annonce_detail'),

    # AJOUTER CETTE LIGNE (Dashboard Privé)
    path('dashboard/biens/<int:pk>/', views.gestion_bien_detail, name='gestion_bien_detail'),

    # Gestion des baux
    path("gestion/baux/add/", views.add_bail, name="add_bail"),
    path("gestion/baux/<int:pk>/", views.bail_detail, name="bail_detail"),
    path(
        "gestion/baux/<int:bail_id>/etat-des-lieux/<str:type_edl>/",
        views.add_etat_des_lieux,
        name="add_etat_des_lieux",
    ),
    path(
        "gestion/baux/<int:bail_id>/generate-pdf/",
        views.generate_lease_pdf,
        name="generate_lease_pdf",
    ),

    # Gestion des loyers
    path("gestion/loyers/", views.loyers_list, name="loyers_list"),
    path(
        "gestion/loyers/<int:loyer_id>/payer/",
        views.mark_loyer_paid,
        name="mark_loyer_paid",
    ),

    # Comptabilité (protégée dans les vues)
    path("comptabilite/grand-livre/", views.grand_livre, name="grand_livre"),
    path("comptabilite/add_depense/", views.add_depense, name="add_depense"),
    path(
        "comptabilite/grand-livre/export/",
        views.export_grand_livre_excel,
        name="export_grand_livre",
    ),

    # ============================================
    # GESTION DOCUMENTS (GED)
    # ============================================
    path("documents/", views.documents_list, name="documents_list"),
    path(
        "document/quittance/<int:loyer_id>/",
        views.download_quittance,
        name="download_quittance",
    ),
    path(
        "document/bail/<int:bail_id>/",
        views.download_contrat,
        name="download_contrat",
    ),
    path(
        "document/kyc/<int:user_id>/<str:doc_type>/",
        views.download_kyc,
        name="download_kyc",
    ),

    # Gestion des interventions
    path("interventions/", views.interventions_list, name="interventions_list"),

    # Actions admin
    path(
        "gestion/actions/generate-rents/",
        views.trigger_rent_generation,
        name="trigger_rent_generation",
    ),

    # ============================================
    # PAIEMENTS
    # ============================================
    path(
        "paiement/initier/<int:loyer_id>/",
        views.initier_paiement,
        name="initier_paiement",
    ),
    path(
        "paiement/simulation/<int:transaction_id>/",
        views.simulation_paiement_gateway,
        name="simulation_paiement_gateway",
    ),
]
