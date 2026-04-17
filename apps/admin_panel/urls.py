from django.urls import path

from .views import (
    AdminPanelDriversListView,
    AdminPanelDriverDetailView,
    AdminPanelRidersListView,
    AdminPanelRiderDetailView,
    AdminPanelDriverVerificationListView,
    AdminPanelDriverVerificationDetailView,
    AdminPanelUploadTypesListView,
    AdminPanelUploadTypesDetailView,
    AdminPanelLegalTypesListView,
    AdminPanelLegalTypesDetailView,
    AdminPanelRegistrationTypesListView,
    AdminPanelRegistrationTypesDetailView,
    AdminPanelTermsTypesListView,
    AdminPanelTermsTypesDetailView,
)

app_name = 'admin_panel'

urlpatterns = [
    path('drivers/', AdminPanelDriversListView.as_view(), name='drivers-list'),
    path('drivers/<int:driver_id>/', AdminPanelDriverDetailView.as_view(), name='drivers-detail'),
    path('riders/', AdminPanelRidersListView.as_view(), name='riders-list'),
    path('riders/<int:rider_id>/', AdminPanelRiderDetailView.as_view(), name='riders-detail'),
    path('verification-drivers/', AdminPanelDriverVerificationListView.as_view(), name='verification-drivers-list'),
    path('verification-drivers/<int:verification_id>/', AdminPanelDriverVerificationDetailView.as_view(), name='verification-drivers-detail'),
    path('upload-driver-identification/', AdminPanelUploadTypesListView.as_view(), name='upload-identification-list'),
    path('upload-driver-identification/<int:upload_type_id>/', AdminPanelUploadTypesDetailView.as_view(), name='upload-identification-detail'),
    path('legal-driver-identification/', AdminPanelLegalTypesListView.as_view(), name='legal-identification-list'),
    path('legal-driver-identification/<int:legal_type_id>/', AdminPanelLegalTypesDetailView.as_view(), name='legal-identification-detail'),
    path('registration-driver-identification/', AdminPanelRegistrationTypesListView.as_view(), name='registration-identification-list'),
    path('registration-driver-identification/<int:registration_type_id>/', AdminPanelRegistrationTypesDetailView.as_view(), name='registration-identification-detail'),
    path('terms-driver-identification/', AdminPanelTermsTypesListView.as_view(), name='terms-identification-list'),
    path('terms-driver-identification/<int:terms_type_id>/', AdminPanelTermsTypesDetailView.as_view(), name='terms-identification-detail'),
]
