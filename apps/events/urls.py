from rest_framework.routers import DefaultRouter

from .views import EventViewSet, HallBookingViewSet, HallViewSet, SphereViewSet

events_router = DefaultRouter()
events_router.register('', EventViewSet, basename='event')

halls_router = DefaultRouter()
halls_router.register('', HallViewSet, basename='hall')

spheres_router = DefaultRouter()
spheres_router.register('', SphereViewSet, basename='sphere')

hall_bookings_router = DefaultRouter()
hall_bookings_router.register('', HallBookingViewSet, basename='hall-booking')
