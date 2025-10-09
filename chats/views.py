# chat/views.py
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q

from .models import Conversation, Message
from accounts.models import CustomUser
from .serializers import ConversationSerializer, MessageSerializer
import uuid
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination
import math
from django.core.paginator import Paginator
from django_filters.rest_framework import DjangoFilterBackend


# Phân trang
class ConversationPagination(PageNumberPagination):
    page_size = 10  # Default value
    currentPage = 1
    user = None

    def get_page_size(self, request):
        # Lấy giá trị pageSize từ query string, nếu có
        page_size = request.query_params.get("pageSize")
        currentPage = request.query_params.get("current")
        self.user = request.user

        # Nếu không có hoặc giá trị không hợp lệ, dùng giá trị mặc định
        self.page_size = int(page_size)
        self.currentPage = int(currentPage)

        try:
            self.page_size = int(page_size) if page_size is not None else self.page_size
        except (ValueError, TypeError):
            self.page_size = self.page_size

        try:
            self.currentPage = (
                int(currentPage) if currentPage is not None else self.currentPage
            )
        except (ValueError, TypeError):
            self.currentPage = self.currentPage

        return self.page_size

    def get_paginated_response(self, data):
        total_count = Conversation.objects.filter(
            Q(user1=self.user) | Q(user2=self.user)
        ).count()
        total_pages = math.ceil(total_count / self.page_size)

        return Response(
            {
                "isSuccess": True,
                "message": "Fetched airport successfully!",
                "meta": {
                    "totalItems": total_count,
                    "currentPage": self.currentPage,
                    "itemsPerPage": self.page_size,
                    "totalPages": total_pages,
                },
                "data": data,
            }
        )


# Lấy danh sách conversation của người dùng hiện tại
class ConversationListView(generics.ListAPIView):
    queryset = Conversation.objects.all()
    serializer_class = ConversationSerializer
    pagination_class = ConversationPagination
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]

    def get_queryset(self):
        user = self.request.user
        queryset = Conversation.objects.filter(Q(user1=user) | Q(user2=user)).order_by(
            "-created_at"
        )

        # Lấy tham số 'current' từ query string để tính toán trang
        current = self.request.query_params.get(
            "current", 1
        )  # Trang hiện tại, mặc định là trang 1
        page_size = self.request.query_params.get(
            "pageSize", 10
        )  # Số phần tử mỗi trang, mặc định là 10

        # Áp dụng phân trang
        paginator = Paginator(queryset, page_size)
        page = paginator.get_page(current)

        return page


# Lấy chi tiết cuộc trò chuyện
class ConversationDetailView(generics.RetrieveAPIView):
    queryset = Conversation.objects.all()
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]


# Gửi tin nhắn mới
class SendMessageView(generics.CreateAPIView):
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        conversation_id = request.data.get("conversation_id")
        text = request.data.get("text")

        try:
            conversation = Conversation.objects.get(id=conversation_id)
        except Conversation.DoesNotExist:
            return Response(
                {"isSuccess": False, "message": "Conversation not found", "data": {}},
                status=status.HTTP_404_NOT_FOUND,
            )

        message = Message.objects.create(
            conversation=conversation,
            sender=request.user,
            text=text,
        )

        # Cập nhật last_message
        conversation.last_message = text
        conversation.seen = False
        conversation.save()

        return Response(
            {
                "isSuccess": True,
                "message": "Message sent successfully",
                "data": MessageSerializer(message).data,
            },
            status=status.HTTP_200_OK,
        )


# Đánh dấu tin nhắn đã xem
class MarkMessagesSeenView(generics.UpdateAPIView):
    permission_classes = [IsAuthenticated]

    def update(self, request, *args, **kwargs):
        conversation_id = request.data.get("conversation_id")

        messages = Message.objects.filter(conversation_id=conversation_id).exclude(
            sender=request.user
        )
        updated_count = messages.update(seen=True)

        return Response(
            {
                "isSuccess": True,
                "message": f"{updated_count} messages marked as seen",
                "data": {},
            },
            status=status.HTTP_200_OK,
        )


class GetOrCreateConversationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        """
        POST body:
        { "user_id": <other_user_id>, "conversation_id": "<optional-uuid-from-client>" }
        Response:
        { "isSuccess": True, "message": "...", "data": { conversation serialized } }
        """
        other_id = request.data.get("user_id") or request.data.get("receiver_id")
        client_conv_id = request.data.get("conversation_id", None)

        if not other_id:
            return Response(
                {"isSuccess": False, "message": "user_id is required", "data": {}},
                status=400,
            )

        try:
            other = CustomUser.objects.get(id=other_id)
        except CustomUser.DoesNotExist:
            return Response(
                {"isSuccess": False, "message": "User not found", "data": {}},
                status=404,
            )

        me = request.user

        # tìm conversation theo 2 chiều
        conversation = Conversation.objects.filter(
            Q(user1=me, user2=other) | Q(user1=other, user2=me)
        ).first()

        if conversation:
            serializer = ConversationSerializer(conversation)
            return Response(
                {
                    "isSuccess": True,
                    "message": "Found conversation",
                    "data": serializer.data,
                }
            )

        # nếu chưa có, tạo mới; nếu client gửi conversation_id (UUID) — dùng nó
        conv_kwargs = {"user1": me, "user2": other}
        if client_conv_id:
            try:
                conv_uuid = uuid.UUID(str(client_conv_id))
                conversation = Conversation.objects.create(id=conv_uuid, **conv_kwargs)
            except ValueError:
                # client gửi id không hợp lệ -> tạo mới id server sinh
                conversation = Conversation.objects.create(**conv_kwargs)
        else:
            conversation = Conversation.objects.create(**conv_kwargs)

        serializer = ConversationSerializer(conversation)
        return Response(
            {
                "isSuccess": True,
                "message": "Conversation created",
                "data": serializer.data,
            },
            status=200,
        )


class MessageListView(APIView):
    def get(self, request, conversation_id):
        try:
            conversation = Conversation.objects.get(id=conversation_id)
        except Conversation.DoesNotExist:
            return Response(
                {"error": "Conversation not found"}, status=status.HTTP_404_NOT_FOUND
            )

        messages = conversation.messages.order_by("created_at")
        serializer = MessageSerializer(messages, many=True)
        return Response(
            {
                "isSuccess": True,
                "message": "Conversation created",
                "data": serializer.data,
            },
            status=200,
        )
