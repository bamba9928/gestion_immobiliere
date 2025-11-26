"""URL configuration for the MADA IMMO project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/stable/topics/http/urls/
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.core.urls')),
    # Django built‑in authentication views (login, logout, password reset, etc.)
    path('accounts/', include('django.contrib.auth.urls')),
    path('api/', include('apps.api.urls')),
]

# Serve media files from MEDIA_ROOT in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
