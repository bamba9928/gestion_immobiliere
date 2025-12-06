from django.contrib.auth import views as auth_views
from django.urls import path

from . import views
from .views import ContactView, add_locataire

urlpatterns = [
    # ============================================
    # PAGES PUBLIQUES (Non authentifiées)
    # ============================================
    path('', views.HomeView.as_view(), name='home'),  # Page d'accueil avec annonces
    path("about/", views.about, name="about"),
    path('comptabilite/grand-livre/', views.grand_livre, name='grand_livre'),
    path('comptabilite/add_depense/', views.add_depense, name='add_depense'),

    # ============================================
    # AUTHENTIFICATION
    # ============================================
    path('login/', auth_views.LoginView.as_view(
        template_name='registration/login.html',
        redirect_authenticated_user=True,
    ), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    # ============================================
    # TABLEAU DE BORD & GESTION (Protégé)
    # ============================================
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/locataires/add/', add_locataire, name='add_locataire'),

    # Gestion des biens
    path('gestion/biens/add/', views.add_bien, name='add_bien'),

    # Gestion des loyers
    path('gestion/loyers/', views.loyers_list, name='loyers_list'),
    path('gestion/loyers/<int:loyer_id>/payer/', views.mark_loyer_paid, name='mark_loyer_paid'),
    path('document/quittance/<int:loyer_id>/', views.download_quittance, name='download_quittance'),

    # Gestion des interventions
    path('interventions/', views.interventions_list, name='interventions_list'),
    # Gestion des baux
    path("gestion/baux/add/", views.add_bail, name="add_bail"),
    path("gestion/baux/<int:pk>/", views.bail_detail, name="bail_detail"),

    # États des lieux
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

    # Actions admin
    path('gestion/actions/generate-rents/', views.trigger_rent_generation, name='trigger_rent_generation'),

    # ============================================
    # PAGES PUBLIQUES SUPPLÉMENTAIRES
    # ============================================
    path('annonce/<int:pk>/', views.AnnonceDetailView.as_view(), name='annonce_detail'),
    path('contact/', ContactView.as_view(), name='contact'),
    path('paiement/initier/<int:loyer_id>/', views.initier_paiement, name='initier_paiement'),
    path('paiement/simulation/<int:transaction_id>/', views.simulation_paiement_gateway, name='simulation_paiement_gateway'),
]