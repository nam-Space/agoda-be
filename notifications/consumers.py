import json
from channels.generic.websocket import AsyncWebsocketConsumer
from django.core.paginator import Paginator
from channels.db import database_sync_to_async
from .models import Notification
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

PAGE_SIZE = 10  # số thông báo mỗi lần trả về


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        if user is None or user.is_anonymous:
            await self.close(code=4001)
            return

        self.user = user
        self.group_name = f"user_{user.id}_notifications"

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        # gửi trang đầu tiên
        await self.send_notifications_page(page_number=1)

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        """Xử lý các message từ client: ví dụ load thêm trang notifications"""
        data = json.loads(text_data)
        action = data.get("action")

        if action == "load_more":
            page = data.get("page", 1)
            try:
                page = int(page)
            except (ValueError, TypeError):
                page = 1
            await self.send_notifications_page(page)

        # Đánh dấu đã đọc 1 thông báo
        elif action == "mark_as_read":
            noti_id = data.get("notification_id")
            if noti_id:
                await self.mark_as_read(noti_id)

    async def send_notifications_page(self, page_number=1):
        notifications_page = await self.get_notifications_page(page_number)

        await self.send(
            text_data=json.dumps(
                {
                    "type": "notifications_page",
                    "page": page_number,
                    "notifications": notifications_page["items"],
                    "has_next": notifications_page["has_next"],
                    "total_unseen": notifications_page["total_unseen"],
                }
            )
        )

    @database_sync_to_async
    def get_total_unseen(self):
        return Notification.objects.filter(user=self.user, is_read=False).count()

    @database_sync_to_async
    def get_notifications_page(self, page_number):
        # Lấy các thông báo user, sắp theo created_at giảm dần
        qs = Notification.objects.filter(user=self.user).order_by("-created_at")
        paginator = Paginator(qs, PAGE_SIZE)
        try:
            page = paginator.page(page_number)
        except:
            # nếu page lớn hơn, trả rỗng
            return {"items": [], "has_next": False}

        # serialize
        items = []
        for n in page.object_list:
            items.append(
                {
                    "id": n.id,
                    "title": n.title,
                    "message": n.message,
                    "link": n.link,
                    "is_read": n.is_read,
                    "is_error": n.is_error,
                    "created_at": n.created_at.isoformat(),
                }
            )

        # thêm thống kê thông báo chưa đọc
        total_unseen = Notification.objects.filter(
            user=self.user, is_read=False
        ).count()

        return {
            "items": items,
            "has_next": page.has_next(),
            "total_unseen": total_unseen,
        }

    async def new_notification(self, event):
        """Khi có noti mới từ server"""
        # emit 1 notification mới
        total_unseen = await self.get_total_unseen()

        await self.send(
            text_data=json.dumps(
                {
                    "type": "new_notification",
                    "title": event.get("title"),
                    "message": event.get("message"),
                    "link": event.get("link"),
                    "created_at": event.get("created_at"),
                    "payload": event.get("payload", None),
                    "total_unseen": total_unseen,
                }
            )
        )

    async def notification_read(self, event):
        await self.send(text_data=json.dumps(event))

    @database_sync_to_async
    def mark_as_read_db(self, noti_id):
        try:
            n = Notification.objects.get(id=noti_id, user=self.user)
            if not n.is_read:
                n.is_read = True
                n.save()
        except Notification.DoesNotExist:
            return None

        total_unseen = Notification.objects.filter(
            user=self.user, is_read=False
        ).count()

        return {"notification_id": noti_id, "total_unseen": total_unseen}

    async def mark_as_read(self, noti_id):
        result = await self.mark_as_read_db(noti_id)

        if result:
            await self.channel_layer.group_send(
                f"user_{self.user.id}_notifications",
                {
                    "type": "notification_read",
                    "notification_id": result["notification_id"],
                    "total_unseen": result["total_unseen"],
                },
            )
