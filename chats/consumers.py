# chats/consumers.py (phiên bản hỗ trợ UUID do frontend truyền)
import json
import uuid
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.db.models import Q
from .models import Conversation, Message
from accounts.models import CustomUser
from .serializers import MessageSerializer, ConversationSerializer
from accounts.serializers import UserSerializer
from asgiref.sync import sync_to_async
from channels.layers import get_channel_layer
from django.db.models import Q, Count

ONLINE_USERS = set()


@sync_to_async
def serialize_users(users_qs):
    return UserSerializer(users_qs, many=True).data


class OnlineConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        """User connect socket: gửi online list + conversations + unseen"""
        user = self.scope["user"]

        if user.is_anonymous:
            await self.close()
            return

        self.user = user
        self.group_name = f"user_{user.id}"

        # Thêm user vào online list
        ONLINE_USERS.add(user.id)

        await self.accept()

        # Join group riêng của user
        await self.channel_layer.group_add(self.group_name, self.channel_name)

        # Join group online chung
        await self.channel_layer.group_add("online_users", self.channel_name)

        # Gửi danh sách online users
        await self.broadcast_online_users()

        # Gửi unseen conversations
        unseen_data = await self.get_unseen_with_latest(user)
        await self.send(
            json.dumps({"type": "unseen_conversations", "data": unseen_data})
        )

    async def disconnect(self, code):
        user = self.user

        if user.id in ONLINE_USERS:
            ONLINE_USERS.remove(user.id)

        await self.channel_layer.group_discard(self.group_name, self.channel_name)
        await self.channel_layer.group_discard("online_users", self.channel_name)

        await self.broadcast_online_users()

    # =========================================================
    # ONLINE USERS
    # =========================================================
    async def broadcast_online_users(self):
        users = await self.get_online_users()
        serialized = await serialize_users(users)

        await self.channel_layer.group_send(
            "online_users", {"type": "online_users_event", "users": serialized}
        )

    async def online_users_event(self, event):
        await self.send(json.dumps({"type": "online_users", "users": event["users"]}))

    @database_sync_to_async
    def get_online_users(self):
        return CustomUser.objects.filter(id__in=ONLINE_USERS)

    @database_sync_to_async
    def get_unseen_with_latest(self, user):
        convs = (
            Conversation.objects.filter(Q(user1=user) | Q(user2=user))
            .annotate(
                unseen_count=Count(
                    "messages",
                    filter=Q(messages__seen=False) & ~Q(messages__sender=user),
                )
            )
            .order_by("-created_at")
        )

        result = []
        for conv in convs:
            latest = conv.messages.order_by("-created_at").first()
            result.append(
                {
                    "conversation": ConversationSerializer(conv).data,
                    "unseen_count": conv.unseen_count,
                    "latest_message": (
                        MessageSerializer(latest).data if latest else None
                    ),
                }
            )
        return result

    # ============================================================================
    # UNSEEN + LATEST MESSAGE
    # ============================================================================
    @database_sync_to_async
    def query_unseen_with_latest(self, user):
        convs = (
            Conversation.objects.filter(Q(user1=user) | Q(user2=user))
            .annotate(
                unseen_count=Count(
                    "messages",
                    filter=Q(messages__seen=False) & ~Q(messages__sender=user),
                )
            )
            .order_by("-created_at")
        )

        result = []
        for conv in convs:
            latest = conv.messages.order_by("-created_at").first()

            result.append(
                {
                    "conversation": ConversationSerializer(conv).data,
                    "unseen_count": conv.unseen_count,
                    "latest_message": (
                        MessageSerializer(latest).data if latest else None
                    ),
                }
            )

        return result

    async def push_unseen_update(self):
        """Gửi unseen + latest message về FE."""
        data = await self.query_unseen_with_latest(self.user)

        await self.send(
            json.dumps(
                {
                    "type": "unseen_conversations",
                    "data": data,
                }
            )
        )

    # ============================================================================
    # NHẬN SỰ KIỆN TỪ ChatConsumer: new_message
    # ============================================================================
    async def new_message(self, event):
        """
        Khi user nhận tin nhắn mới:
        - cập nhật unseen conversations
        - cập nhật latest message
        - đẩy về FE ngay lập tức
        """
        # event["message"] chứa object tin nhắn mới

        await self.push_unseen_update()

        # đẩy sự kiện "new_message_received" riêng biệt (tuỳ frontend dùng)
        await self.send(
            json.dumps(
                {
                    "type": "new_message_received",
                    "message": event["message"],
                }
            )
        )


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

        # 1) Nếu là action đánh dấu đã seen
        if data.get("action") == "seen":

            await self.mark_seen(conversation_id=client_conv_id, user_id=sender_id)

            # Gửi cập nhật về chính user đang xem chat
            await self.send(
                json.dumps({"type": "seen_update", "conversation_id": client_conv_id})
            )

            # Gửi cho OnlineConsumer để update unseen_count
            await self.channel_layer.group_send(
                f"user_{receiver_id}",
                {
                    "type": "new_message",
                    "message": {
                        "side": "receiver",
                        "user_id": sender_id,
                    },
                },
            )

            return

        if not message or not sender_id or not receiver_id:
            return

        # lưu message (hàm sync chuyển sang async bằng decorator)
        saved_message = await self.save_message(
            sender_id, receiver_id, message, self.conversation_id or client_conv_id
        )

        await self.mark_seen(conversation_id=self.conversation_id, user_id=sender_id)

        # broadcast tới nhóm conversation (sử dụng conversation_id thực tế)
        await self.channel_layer.group_send(
            f"chat_{saved_message['conversation_id']}",
            {
                "type": "chat_message",
                "message": saved_message,
            },
        )

        await self.channel_layer.group_send(
            f"user_{receiver_id}",
            {"type": "new_message", "message": saved_message},
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event["message"]))

    @database_sync_to_async
    def mark_seen(self, conversation_id, user_id):
        try:
            conv = Conversation.objects.get(id=conversation_id)

            # Đánh dấu tất cả tin nhắn mà mình là người nhận
            Message.objects.filter(conversation=conv, seen=False).exclude(
                sender_id=user_id
            ).update(seen=True)

            # Cập nhật conversation
            conv.seen = True
            conv.save()

        except Conversation.DoesNotExist:
            pass

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
