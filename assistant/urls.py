"""Root URL configuration."""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path

from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
)

from apps.core.views_legacy import LegacyAssetView, LegacyStaticView

admin.site.site_header = settings.ADMIN_SITE_HEADER
admin.site.site_title = settings.ADMIN_SITE_TITLE
admin.site.index_title = settings.ADMIN_INDEX_TITLE

urlpatterns = [
    # Django built-in admin (emergency vositasi)
    path('admin/django/', admin.site.urls),

    # API
    path('api/', include('apps.api_urls')),

    # OpenAPI schema
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path(
        'api/schema/swagger-ui/',
        SpectacularSwaggerView.as_view(url_name='schema'),
        name='swagger-ui',
    ),

    # Legacy production frontend (JAR ichidan ko'chirildi — referens sifatida ko'rsatish uchun)
    path('legacy/', LegacyStaticView.as_view()),
    re_path(r'^legacy/(?P<path>.*)$', LegacyStaticView.as_view()),

    # Legacy static assetlari production yo'llarida (`/static/...`, `/favicon.ico`)
    re_path(r'^(?P<path>static/.*)$', LegacyAssetView.as_view()),
    path('favicon.ico', LegacyAssetView.as_view(), {'path': 'favicon.ico'}),
    path('favicon-16x16.png', LegacyAssetView.as_view(), {'path': 'favicon-16x16.png'}),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
