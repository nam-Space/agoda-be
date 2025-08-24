from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from .views import RoomViewSet, RoomImageViewSet

router = DefaultRouter()
router.register(r"rooms", RoomViewSet)
router.register(r"room-images", RoomImageViewSet)

urlpatterns = [
    path("", include(router.urls)),
]

# Thêm vào để phục vụ các file media trong quá trình phát triển
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
