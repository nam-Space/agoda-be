from django.db import models
from django.conf import settings
from django.core.mail import send_mail
from accounts.models import CustomUser


class Notification(models.Model):
    user = models.ForeignKey(
        CustomUser, null=True, blank=True, on_delete=models.CASCADE
    )
    email = models.EmailField(null=True, blank=True)  # email trực tiếp
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        creating = self._state.adding
        super().save(*args, **kwargs)
        recipient = self.email or (self.user.email if self.user else None)
        if creating and recipient:
            send_mail(
                subject=self.title,
                message=self.message,
                from_email=None,
                recipient_list=[recipient],
                fail_silently=False,
            )
