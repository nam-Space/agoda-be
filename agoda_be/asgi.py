import os
from django.core.asgi import get_asgi_application

# ⚠️ 1. Cấu hình môi trường trước
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "agoda_be.settings")

# ⚠️ 2. Load Django trước khi import channels
django_asgi_app = get_asgi_application()

# ⚠️ 3. Sau khi Django đã load, mới import Channels-related modules
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator
import chats.routing  # <-- Bây giờ mới an toàn để import
from agoda_be.middleware import JWTAuthMiddleware
import notifications.routing

# ⚙️ 4. Tạo ứng dụng ASGI
application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AllowedHostsOriginValidator(
            JWTAuthMiddleware(
                URLRouter(
                    chats.routing.websocket_urlpatterns
                    + notifications.routing.websocket_urlpatterns
                )
            )
        ),
    }
)
