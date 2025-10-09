# chat/models.py
from django.db import models
from django.conf import settings
from accounts.models import CustomUser
import uuid


class Conversation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user1 = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name="conversations_started"
    )
    user2 = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name="conversations_received"
    )
    sender = models.ForeignKey(
        CustomUser, related_name="last_sender", null=True, on_delete=models.SET_NULL
    )
    last_message = models.TextField(null=True, blank=True)
    seen = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Conversation between {self.user1.username} and {self.user2.username}"


class Message(models.Model):
    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="messages"
    )
    sender = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name="sent_messages"
    )
    text = models.TextField()
    seen = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message from {self.sender.username} in {self.conversation.id}"
