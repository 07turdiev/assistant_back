"""URL'lar:
/api/drafts/events/         — list/create
/api/drafts/events/{id}/    — retrieve/update/destroy
/api/drafts/events/{id}/publish/ — POST joylash
/api/drafts/events/{id}/reject/  — POST rad etish

Reports uchun ham xuddi shu pattern.
"""
from rest_framework.routers import DefaultRouter

from .views import EventDraftViewSet, ReportDraftViewSet

router = DefaultRouter()
router.register(r'events', EventDraftViewSet, basename='event-drafts')
router.register(r'reports', ReportDraftViewSet, basename='report-drafts')

urlpatterns = router.urls
