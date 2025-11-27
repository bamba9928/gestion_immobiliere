from django.urls import path
from .views import MobileBienListView, BienDetailView
from .views import MobileBienListView, BienDetailView, InterventionListCreateView

urlpatterns = [
    path('mobile/biens/', MobileBienListView.as_view(), name='api-mobile-biens'),
    path('mobile/biens/<int:pk>/', BienDetailView.as_view(), name='api-mobile-bien-detail'),
    path('mobile/interventions/', InterventionListCreateView.as_view(), name='api-mobile-interventions'),
]