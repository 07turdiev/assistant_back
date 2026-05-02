"""Yagona /api/ URL konfiguratsiyasi."""
from django.urls import include, path

from apps.events.urls import events_router, pre_events_router
from apps.notifications.urls import notifications_urlpatterns, webpush_urlpatterns
from apps.organisations.urls import (
    districts_router,
    organisations_router,
    regions_router,
)

urlpatterns = [
    path('auth/', include('apps.auth_app.urls')),
    path('users/', include('apps.users.urls')),
    path('directions/', include('apps.directions.urls')),
    path('organisations/', include(organisations_router.urls)),
    path('regions/', include(regions_router.urls)),
    path('districts/', include(districts_router.urls)),
    path('events/', include(events_router.urls)),
    path('pre-events/', include(pre_events_router.urls)),
    path('notifications/', include(notifications_urlpatterns)),
    path('webpush/', include(webpush_urlpatterns)),
    path('file/', include('apps.attachments.urls')),
    path('info/', include('apps.info.urls')),
]
