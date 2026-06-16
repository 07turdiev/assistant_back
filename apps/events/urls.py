from rest_framework.routers import DefaultRouter

from .views import EventViewSet

events_router = DefaultRouter()
events_router.register('', EventViewSet, basename='event')
