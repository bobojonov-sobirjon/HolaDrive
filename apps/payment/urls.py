from django.urls import path

from .views import SavedCardDetailView, SavedCardListCreateView
from .views_connect import (
    DriverCheckoutHistoryView,
    DriverStripeBalanceView,
    DriverStripeConnectBankAccountView,
    DriverStripeConnectCompleteSetupView,
)

app_name = 'payment'

urlpatterns = [
    path('saved-cards/', SavedCardListCreateView.as_view(), name='saved-card-list'),
    path('saved-cards/<int:pk>/', SavedCardDetailView.as_view(), name='saved-card-detail'),
    # Driver Stripe Connect (AutoHandy "Master" equivalent)
    path(
        'driver/stripe-connect/bank-account/',
        DriverStripeConnectBankAccountView.as_view(),
        name='driver-stripe-connect-bank',
    ),
    path(
        'driver/stripe-connect/complete-setup/',
        DriverStripeConnectCompleteSetupView.as_view(),
        name='driver-stripe-connect-complete-setup',
    ),
    path('driver/stripe-balance/', DriverStripeBalanceView.as_view(), name='driver-stripe-balance'),
    path('driver/checkout-history/', DriverCheckoutHistoryView.as_view(), name='driver-checkout-history'),
]
