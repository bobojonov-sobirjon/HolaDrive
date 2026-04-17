from django.urls import path

from .views import SavedCardDetailView, SavedCardListCreateView

app_name = 'payment'

urlpatterns = [
    path('saved-cards/', SavedCardListCreateView.as_view(), name='saved-card-list'),
    path('saved-cards/<int:pk>/', SavedCardDetailView.as_view(), name='saved-card-detail'),
]
