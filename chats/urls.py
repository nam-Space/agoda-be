# chat/urls.py
from django.urls import path
from .views import (
    ConversationListView,
    ConversationDetailView,
    SendMessageView,
    MarkMessagesSeenView,
    GetOrCreateConversationView,
    MessageListView,
)

urlpatterns = [
    path("conversations/", ConversationListView.as_view(), name="conversation-list"),
    path(
        "conversations/<int:pk>/",
        ConversationDetailView.as_view(),
        name="conversation-detail",
    ),
    path("messages/send/", SendMessageView.as_view(), name="send-message"),
    path("messages/seen/", MarkMessagesSeenView.as_view(), name="mark-seen"),
    path(
        "conversations/get_or_create/",
        GetOrCreateConversationView.as_view(),
        name="conversation-get-or-create",
    ),
    path(
        "messages/<str:conversation_id>/",
        MessageListView.as_view(),
        name="message-list",
    ),
]
