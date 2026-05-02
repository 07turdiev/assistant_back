from rest_framework.routers import DefaultRouter

from .views import DistrictViewSet, OrganisationViewSet, RegionViewSet

regions_router = DefaultRouter()
regions_router.register('', RegionViewSet, basename='region')

districts_router = DefaultRouter()
districts_router.register('', DistrictViewSet, basename='district')

organisations_router = DefaultRouter()
organisations_router.register('', OrganisationViewSet, basename='organisation')
