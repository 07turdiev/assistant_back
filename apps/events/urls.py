from rest_framework.routers import DefaultRouter

from .views import EventViewSet, PreEventViewSet

events_router = DefaultRouter()
events_router.register('', EventViewSet, basename='event')

pre_events_router = DefaultRouter()
pre_events_router.register('', PreEventViewSet, basename='pre-event')
