"""URL routes for the core application."""
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Dashboard for administrators and tenants
    path('', views.dashboard, name='dashboard'),
    # Authentication
    path('login/', auth_views.LoginView.as_view(
        template_name='login.html',
        redirect_authenticated_user=True,
    ), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    # Document download
    path('document/quittance/<int:loyer_id>/', views.download_quittance, name='download_quittance'),
]
