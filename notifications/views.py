from rest_framework import viewsets, permissions
from .models import Notification
from .serializers import NotificationSerializer

class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated] 

    def get_queryset(self):
        # mỗi user chỉ thấy notification của mình
        user = self.request.user
        return Notification.objects.filter(user=user)

    def get_permissions(self):
        if self.action == 'create':
            # Cho phép anyone tạo notification
            return [permissions.AllowAny()]
        # Các action khác yêu cầu login
        return [permissions.IsAuthenticated()]