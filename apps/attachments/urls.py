from django.urls import path

from .views import FileDownloadView

urlpatterns = [
    path('<uuid:pk>/', FileDownloadView.as_view(), name='file-download'),
]
