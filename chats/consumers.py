# chats/consumers.py (phiên bản hỗ trợ UUID do frontend truyền)
import json
import uuid
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.db.models import Q
from .models import Conversation, Message
from accounts.models import CustomUser
from .serializers import MessageSerializer


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.conversation_id = self.scope["url_route"]["kwargs"].get("conversation_id")
        self.room_group_name = f"chat_{self.conversation_id}"
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data.get("message") or data.get("text")
        sender_id = data.get("sender_id")
        receiver_id = data.get("receiver_id")  # id của người nhận (user id)
        client_conv_id = data.get("conversation_id")  # optional, client may pass too

        if not message or not sender_id or not receiver_id:
            return

        # lưu message (hàm sync chuyển sang async bằng decorator)
        saved_message = await self.save_message(
            sender_id, receiver_id, message, self.conversation_id or client_conv_id
        )

        # broadcast tới nhóm conversation (sử dụng conversation_id thực tế)
        await self.channel_layer.group_send(
            f"chat_{saved_message['conversation_id']}",
            {
                "type": "chat_message",
                "message": saved_message,
            },
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event["message"]))

    @database_sync_to_async
    def save_message(
        self, sender_id, receiver_id, message_text, conv_id_candidate=None
    ):
        # lấy sender/receiver
        sender = CustomUser.objects.filter(id=sender_id).first()
        receiver = CustomUser.objects.filter(id=receiver_id).first()
        if not sender or not receiver:
            return {"error": "Invalid sender or receiver"}

        conversation = None

        # 1) nếu client truyền conv_id_candidate (string) -> thử parse và lấy conversation
        if conv_id_candidate:
            try:
                conv_uuid = uuid.UUID(str(conv_id_candidate))
                conversation = Conversation.objects.filter(id=conv_uuid).first()
            except ValueError:
                conversation = None

        # 2) nếu chưa có, tìm conversation giữa 2 user (cả 2 chiều)
        if not conversation:
            conversation = Conversation.objects.filter(
                Q(user1=sender, user2=receiver) | Q(user1=receiver, user2=sender)
            ).first()

        # 3) nếu vẫn chưa có, tạo mới; nếu client đã đưa conv_uuid hợp lệ nhưng chưa tồn tại -> tạo với id đó
        if not conversation:
            if conv_id_candidate:
                try:
                    conv_uuid = uuid.UUID(str(conv_id_candidate))
                    conversation = Conversation.objects.create(
                        id=conv_uuid, user1=sender, user2=receiver
                    )
                except ValueError:
                    conversation = Conversation.objects.create(
                        user1=sender, user2=receiver
                    )
            else:
                conversation = Conversation.objects.create(user1=sender, user2=receiver)

        # tạo message
        msg = Message.objects.create(
            conversation=conversation, sender=sender, text=message_text
        )
        # cập nhật conversation
        conversation.last_message = message_text
        conversation.sender = sender
        conversation.seen = False
        conversation.save()

        serializer = MessageSerializer(msg)
        data = serializer.data

        # ✅ Bổ sung conversation_id thủ công để group_send không bị lỗi
        data["conversation_id"] = str(conversation.id)

        return data
