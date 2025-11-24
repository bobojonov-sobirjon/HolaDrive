from django.urls import path
from .views import (
    OrderCreateView,
    PriceEstimateView,
    OrderItemUpdateView,
    OrderItemManagePriceView,
    OrderCancelView,
    MyOrderListView,
    OrderPreferencesCreateView,
    AdditionalPassengerCreateView,
    OrderScheduleCreateView
)

urlpatterns = [
    path('create/', OrderCreateView.as_view(), name='order-create'),
    path('my-orders/', MyOrderListView.as_view(), name='my-orders'),
    path('price-estimate/', PriceEstimateView.as_view(), name='price-estimate'),
    path('order-item/<int:order_item_id>/update/', OrderItemUpdateView.as_view(), name='order-item-update'),
    path('order-item/<int:order_item_id>/manage-price/', OrderItemManagePriceView.as_view(), name='order-item-manage-price'),
    path('<int:order_id>/cancel/', OrderCancelView.as_view(), name='order-cancel'),
    path('preferences/', OrderPreferencesCreateView.as_view(), name='order-preferences-create'),
    path('additional-passenger/', AdditionalPassengerCreateView.as_view(), name='additional-passenger-create'),
    path('schedule/', OrderScheduleCreateView.as_view(), name='order-schedule-create'),
]