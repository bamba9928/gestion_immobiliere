"""URL routes for the API layer of MADA IMMO."""
from django.urls import path

from .views import MobileBienListView


urlpatterns = [
    path('mobile/biens/', MobileBienListView.as_view(), name='api-mobile-biens'),
]
