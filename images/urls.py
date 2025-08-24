# images/urls.py

from django.urls import path
from .views import UploadImageView

urlpatterns = [
    path("upload-image/", UploadImageView.as_view(), name="upload-image"),
]
