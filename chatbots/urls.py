from django.urls import path
from .views import fetch_session, create_new_chat, ask_chatbot, get_messages

urlpatterns = [
    path("session/", fetch_session, name="get-session"),
    path("new/", create_new_chat, name="create-new-chat"),
    path("ask/", ask_chatbot, name="ask-chatbot"),
    path("messages/", get_messages, name="get-messages"),
]
