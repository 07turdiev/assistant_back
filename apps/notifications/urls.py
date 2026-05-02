"""URL'lar — frontend kutgan formatga to'liq mos.

Frontend axios:
- GET    /api/notifications/?page=
- GET    /api/notifications/count/
- DELETE /api/notifications/{id}/
- POST   /api/notifications/bulk-delete/
- POST   /api/notifications/mark-read/
- GET    /api/webpush/vapid-public-key/
- POST   /api/webpush/subscribe/
- DELETE /api/webpush/subscribe/{id}/
- GET    /api/webpush/subscriptions/
- POST   /api/webpush/test/
"""
from django.urls import path

from .views import (
    NotificationViewSet,
    VapidPublicKeyView,
    WebPushSubscriptionViewSet,
)

# DRF Router viewset'ning custom action'lari uchun yo'l yaratishda chigallashadi —
# qo'lda yozish ko'p qulayroq.

notification_list = NotificationViewSet.as_view({'get': 'list'})
notification_all = NotificationViewSet.as_view({'get': 'all'})
notification_count = NotificationViewSet.as_view({'get': 'count'})
notification_detail = NotificationViewSet.as_view({'delete': 'destroy_one'})
notification_bulk_delete = NotificationViewSet.as_view({'post': 'bulk_delete'})
notification_mark_read = NotificationViewSet.as_view({'post': 'mark_read'})

notifications_urlpatterns = [
    path('', notification_list, name='notifications-list'),
    path('all/', notification_all, name='notifications-all'),
    path('count/', notification_count, name='notifications-count'),
    path('bulk-delete/', notification_bulk_delete, name='notifications-bulk-delete'),
    path('mark-read/', notification_mark_read, name='notifications-mark-read'),
    path('<uuid:pk>/', notification_detail, name='notifications-detail'),
]


webpush_subscribe = WebPushSubscriptionViewSet.as_view({'post': 'subscribe'})
webpush_test = WebPushSubscriptionViewSet.as_view({'post': 'test'})
webpush_subscriptions = WebPushSubscriptionViewSet.as_view({'get': 'list'})
webpush_destroy = WebPushSubscriptionViewSet.as_view({'delete': 'destroy'})

webpush_urlpatterns = [
    path('vapid-public-key/', VapidPublicKeyView.as_view(), name='webpush-vapid-public-key'),
    path('subscribe/', webpush_subscribe, name='webpush-subscribe'),
    path('subscribe/<uuid:pk>/', webpush_destroy, name='webpush-unsubscribe'),
    path('subscriptions/', webpush_subscriptions, name='webpush-subscriptions'),
    path('test/', webpush_test, name='webpush-test'),
]
