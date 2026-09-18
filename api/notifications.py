import logging
import requests
from .models import DeviceToken

logger = logging.getLogger(__name__)

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"


def send_push_notification_for_insight(user, insight):
    tokens = list(DeviceToken.objects.filter(user=user).values_list("expo_push_token", flat=True))
    if not tokens:
        return

    messages = [
        {
            "to": token,
            "sound": "default",
            "title": "Paylio Advisor Alert",
            "body": insight.summary,
            "data": {
                "insightId": insight.id,
                "severity": insight.severity,
            },
        }
        for token in tokens
    ]

    try:
        response = requests.post(
            EXPO_PUSH_URL,
            json=messages,
            headers={
                "Accept": "application/json",
                "Accept-Encoding": "gzip, deflate",
                "Content-Type": "application/json",
            },
            timeout=5,
        )
        response.raise_for_status()
    except Exception as exc:
        logger.warning("Failed to send push notification to user %s: %s", user.id, exc)
