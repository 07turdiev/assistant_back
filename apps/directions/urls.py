from rest_framework.routers import DefaultRouter

from .views import DirectionViewSet

router = DefaultRouter()
router.register('', DirectionViewSet, basename='direction')

urlpatterns = router.urls
