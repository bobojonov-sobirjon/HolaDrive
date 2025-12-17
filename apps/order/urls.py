from django.urls import path
from .views import (
    OrderCreateView,
    PriceEstimateView,
    OrderItemUpdateView,
    OrderItemManagePriceView,
    OrderCancelView,
    MyOrderListView,
    OrderPreferencesGetView,
    OrderPreferencesCreateView,
    AdditionalPassengerCreateView,
    OrderScheduleCreateView,
    DriverNearbyOrdersView,
    DriverOrderActionView,
    DriverLocationUpdateView,
    DriverLocationForOrderView,
    DriverEarningsView,
    DriverRideHistoryView,
    DriverOnlineStatusView,
    TripRatingCreateView,
    RatingFeedbackTagsListView,
)

urlpatterns = [
    path('create/', OrderCreateView.as_view(), name='order-create'),
    path('my-orders/', MyOrderListView.as_view(), name='my-orders'),
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

    # Real-time tracking
    path('driver/location/update/', DriverLocationUpdateView.as_view(), name='driver-location-update'),
    path('<int:order_id>/driver/location/', DriverLocationForOrderView.as_view(), name='driver-location-for-order'),

    # Driver earnings and ride history
    path('driver/earnings/', DriverEarningsView.as_view(), name='driver-earnings'),
    path('driver/ride-history/', DriverRideHistoryView.as_view(), name='driver-ride-history'),
    path('driver/online-status/', DriverOnlineStatusView.as_view(), name='driver-online-status'),

    # Trip rating
    path('rating/create/', TripRatingCreateView.as_view(), name='trip-rating-create'),
    path('rating/feedback-tags/', RatingFeedbackTagsListView.as_view(), name='rating-feedback-tags'),
]