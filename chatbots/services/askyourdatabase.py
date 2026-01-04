import requests
from django.conf import settings

BASE_URL = "https://www.askyourdatabase.com"


def fetch_session_service(body: dict):
    # đảm bảo có chatbotid (đúng key, đúng lowercase)
    body.setdefault("chatbotid", settings.AYD_CHATBOT_ID)
    body.setdefault("name", "none")
    body.setdefault("email", "none@none.com")
    body.setdefault("oId", "6371")

    response = requests.post(
        f"{BASE_URL}/api/chatbot/v2/session",
        headers={
            "Authorization": f"Bearer {settings.AYD_API_KEY}",
            "Content-Type": "application/json",
        },
        json=body,
        timeout=15,
    )

    if response.status_code != 200:
        print("STATUS:", response.status_code)
        print("RESPONSE:", response.text)

    response.raise_for_status()
    return response.json()
