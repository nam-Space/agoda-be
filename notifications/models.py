from django.db import models
from django.conf import settings
from django.core.mail import send_mail
from accounts.models import CustomUser
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


class Notification(models.Model):
    user = models.ForeignKey(
        CustomUser, null=True, blank=True, on_delete=models.CASCADE
    )
    email = models.EmailField(null=True, blank=True)  # email trực tiếp
    title = models.CharField(max_length=255)
    message = models.TextField(null=True, blank=True)
    message_email = models.TextField(null=True, blank=True)
    is_read = models.BooleanField(default=False)
    is_error = models.BooleanField(default=False)
    link = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __init__(self, *args, **kwargs):
        # Lấy tham số đặc biệt, không phải field model
        self._send_mail_flag = kwargs.pop("send_mail_flag", True)  # mặc định gửi mail
        super().__init__(*args, **kwargs)

    def save(self, *args, **kwargs):
        creating = self._state.adding
        super().save(*args, **kwargs)

        recipient = self.email or (self.user.email if self.user else None)
        if creating and recipient and self._send_mail_flag:
            try:
                # gửi email (nếu cần)
                send_mail(
                    subject=self.title,
                    message=self.message,
                    from_email=None,
                    recipient_list=[recipient],
                    html_message=self.message_email,
                    fail_silently=False,
                )
            except Exception as e:
                # Log lỗi (dùng logging hoặc print cho dev)
                import logging

                logger = logging.getLogger(__name__)
                logger.error(f"Failed to send email to {recipient}: {str(e)}")
                # Có thể set flag lỗi nếu cần: self.is_error = True; self.save(update_fields=['is_error'])

        # Gửi realtime đến user (nếu có)
        if creating and self.user:
            channel_layer = get_channel_layer()
            payload = {
                "type": "new_notification",  # maps to NotificationConsumer.new_notification
                "title": self.title,
                "message": self.message,
                "link": self.link,
                "created_at": self.created_at.isoformat(),
                "payload": {
                    "notification_id": self.id,
                    # thêm các dữ liệu khác nếu cần
                },
            }
            try:
                # async_to_sync để gọi từ sync context (save)
                async_to_sync(channel_layer.group_send)(
                    f"user_{self.user.id}_notifications", payload
                )
            except Exception as e:
                # Log lỗi (dùng logging hoặc print cho dev)
                import logging

                logger = logging.getLogger(__name__)
                logger.error(f"Failed to send group to user: {str(e)}")
