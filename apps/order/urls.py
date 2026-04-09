from django.urls import path
from .views import (
    OrderCreateView,
    PriceEstimateView,
    OrderItemUpdateView,
    OrderItemManagePriceView,
    OrderCancelView,
    MyOrderListView,
    OrderDetailView,
    OrderPreferencesGetView,
    OrderPreferencesCreateView,
    AdditionalPassengerCreateView,
    OrderScheduleCreateView,
    DriverNearbyOrdersView,
    DriverOrderActionView,
    DriverPickupView,
    DriverCompleteView,
    DriverCancelOrderView,
    DriverLocationUpdateView,
    DriverLocationForOrderView,
    DriverDashboardView,
    DriverEarningsView,
    DriverCashoutHistoryView,
    DriverCashoutCreateView,
    DriverRideHistoryView,
    DriverOnlineStatusView,
    TripRatingCreateView,
    DriverRiderRatingCreateView,
    RatingFeedbackTagsListView,
    OrderChatDetailView,
    OrderChatMessagesView,
)

urlpatterns = [
    path('create/', OrderCreateView.as_view(), name='order-create'),
    path('my-orders/', MyOrderListView.as_view(), name='my-orders'),
    path('<int:order_id>/', OrderDetailView.as_view(), name='order-detail'),
    path('price-estimate/', PriceEstimateView.as_view(), name='price-estimate'),
    path('order-item/<int:order_item_id>/update/', OrderItemUpdateView.as_view(), name='order-item-update'),
    path('order-item/<int:order_item_id>/manage-price/', OrderItemManagePriceView.as_view(), name='order-item-manage-price'),
    path('<int:order_id>/cancel/', OrderCancelView.as_view(), name='order-cancel'),
    path('preferences/', OrderPreferencesGetView.as_view(), name='order-preferences-get'),
    path('preferences/create/', OrderPreferencesCreateView.as_view(), name='order-preferences-create'),
    path('additional-passenger/', AdditionalPassengerCreateView.as_view(), name='additional-passenger-create'),
    path('schedule/', OrderScheduleCreateView.as_view(), name='order-schedule-create'),

    # Advanced driver features
    path('driver/nearby-orders/', DriverNearbyOrdersView.as_view(), name='driver-nearby-orders'),
    path('driver/order-action/', DriverOrderActionView.as_view(), name='driver-order-action'),
    path('driver/pickup/', DriverPickupView.as_view(), name='driver-pickup'),
    path('driver/complete/', DriverCompleteView.as_view(), name='driver-complete'),
    path('driver/cancel/', DriverCancelOrderView.as_view(), name='driver-cancel'),

    # Real-time tracking
    path('driver/location/update/', DriverLocationUpdateView.as_view(), name='driver-location-update'),
    path('<int:order_id>/driver/location/', DriverLocationForOrderView.as_view(), name='driver-location-for-order'),

    # Driver dashboard (Figma Earnings: overview, cash_history, ride_history)
    path('driver/dashboard/', DriverDashboardView.as_view(), name='driver-dashboard'),
    path('driver/earnings/', DriverEarningsView.as_view(), name='driver-earnings'),
    path('driver/cash-history/', DriverCashoutHistoryView.as_view(), name='driver-cash-history'),
    path('driver/cashout/', DriverCashoutCreateView.as_view(), name='driver-cashout-create'),
    path('driver/ride-history/', DriverRideHistoryView.as_view(), name='driver-ride-history'),
    path('driver/online-status/', DriverOnlineStatusView.as_view(), name='driver-online-status'),

    # Trip rating
    path('rating/create/', TripRatingCreateView.as_view(), name='trip-rating-create'),
    path('driver/rating/create/', DriverRiderRatingCreateView.as_view(), name='driver-rider-rating-create'),
    path('rating/feedback-tags/', RatingFeedbackTagsListView.as_view(), name='rating-feedback-tags'),

    # Order chat (Rider <-> Driver)
    path('<int:order_id>/chat/', OrderChatDetailView.as_view(), name='order-chat-detail'),
    path('<int:order_id>/chat/messages/', OrderChatMessagesView.as_view(), name='order-chat-messages'),
]