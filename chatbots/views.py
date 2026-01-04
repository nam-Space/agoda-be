from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .services.askyourdatabase import fetch_session_service
import json
import requests
from django.conf import settings
from django.http import JsonResponse, StreamingHttpResponse
import httpx
from asgiref.sync import async_to_sync
import asyncio
from accounts.models import CustomUser

BASE_URL = "https://www.askyourdatabase.com"


@csrf_exempt
def fetch_session(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    body = json.loads(request.body or "{}")

    try:
        data = fetch_session_service(body)
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
def ask_chatbot(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        body = json.loads(request.body)
        question = body.get("question")
        chatid = body.get("chatid")
        debug = body.get("debug", True)

        if not question or not chatid:
            return JsonResponse(
                {"error": "question and chatid are required"}, status=400
            )

        client = httpx.Client(timeout=None)

        def event_stream():
            with client.stream(
                "POST",
                f"{BASE_URL}/api/ask",
                headers={
                    "Authorization": f"Bearer {settings.AYD_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "question": question,
                    "botid": settings.AYD_CHATBOT_ID,
                    "chatid": chatid,
                    "debug": debug,
                },
            ) as response:
                for chunk in response.iter_bytes():
                    yield chunk

        response = StreamingHttpResponse(
            event_stream(),
            content_type="text/event-stream",
        )
        response["Cache-Control"] = "no-cache"
        response["Connection"] = "keep-alive"
        response["X-Accel-Buffering"] = "no"

        return response

    except Exception as e:
        print("ask_chatbot error:", e)
        return JsonResponse({"error": "Internal server error"}, status=500)


@csrf_exempt
def create_new_chat(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        body = json.loads(request.body or "{}")
        user_id = body.get("user_id")

        if not user_id:
            return JsonResponse({"error": "user_id is required"}, status=400)

        # 1️⃣ Lấy user
        try:
            user = CustomUser.objects.get(id=user_id)
        except CustomUser.DoesNotExist:
            return JsonResponse({"error": "User not found"}, status=404)

        # 2️⃣ Nếu user đã có chatbot → trả luôn
        if user.chatbot_id:
            return JsonResponse(
                {
                    "chatid": user.chatbot_id,
                    "user_id": user.id,
                    "message": "Chat already exists",
                }
            )

        # 3️⃣ Chưa có → tạo chat mới từ AskYourDatabase
        response = requests.post(
            f"{BASE_URL}/api/chatbot/newChat",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {settings.AYD_API_KEY}",
            },
            json={
                "botid": settings.AYD_CHATBOT_ID,
            },
            timeout=30,
        )

        if response.status_code != 200:
            return JsonResponse(
                {"error": response.text},
                status=response.status_code,
            )

        data = response.json()

        chat_id = data.get("chatid") or data.get("id")
        if not chat_id:
            return JsonResponse(
                {"error": "chatid not found in response"},
                status=500,
            )

        # 4️⃣ Lưu chatbot_id vào user
        user.chatbot_id = chat_id
        user.save(update_fields=["chatbot_id"])

        # 5️⃣ Trả kết quả
        return JsonResponse(
            {
                "chatid": chat_id,
                "user_id": user.id,
                "message": "Chat created successfully",
            }
        )

    except Exception as e:
        print("Error creating new chat:", e)
        return JsonResponse(
            {"error": "Internal server error"},
            status=500,
        )


@csrf_exempt
def get_messages(request):
    if request.method != "GET":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        chatid = request.GET.get("chatid")
        debug = request.GET.get("debug", "true")
        timestamp = request.GET.get("timestamp")

        if not chatid:
            return JsonResponse({"error": "chatid is required"}, status=400)

        params = {
            "botid": settings.AYD_CHATBOT_ID,
            "chatid": chatid,
            "debug": debug,
        }

        if timestamp:
            params["timestamp"] = timestamp

        response = requests.get(
            f"{BASE_URL}/api/chatbot/messages",
            headers={
                "Authorization": f"Bearer {settings.AYD_API_KEY}",
            },
            params=params,
        )

        if response.status_code != 200:
            return JsonResponse(
                {"error": f"Failed to get chat messages: {response.text}"},
                status=response.status_code,
            )

        data = response.json()
        return JsonResponse(data, safe=False)

    except Exception as e:
        print("Error getting chat messages:", e)
        return JsonResponse({"error": "Internal server error"}, status=500)
