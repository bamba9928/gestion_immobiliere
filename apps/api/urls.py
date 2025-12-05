from django.urls import path

from .views import BienDetailView, InterventionListCreateView, BienListView

urlpatterns = [
    path('biens/mobile/', BienListView.as_view()),
    path('mobile/biens/<int:pk>/', BienDetailView.as_view(), name='api-mobile-biens-detail'),
    path('mobile/interventions/', InterventionListCreateView.as_view(), name='api-mobile-interventions'),
]