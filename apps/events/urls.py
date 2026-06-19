from rest_framework.routers import DefaultRouter

from .views import EventViewSet, HallViewSet

events_router = DefaultRouter()
events_router.register('', EventViewSet, basename='event')

halls_router = DefaultRouter()
halls_router.register('', HallViewSet, basename='hall')
