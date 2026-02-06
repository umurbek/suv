import requests
from django.conf import settings

FCM_LEGACY_URL = 'https://fcm.googleapis.com/fcm/send'


def send_fcm(tokens, title: str, body: str, data: dict = None) -> dict:
    """Send FCM push using legacy API. `tokens` can be a single token or list of tokens."""
    if not settings.FCM_ENABLED:
        return {'error': 'FCM not configured on server'}

    if isinstance(tokens, str):
        payload = {
            'to': tokens,
            'notification': {'title': title, 'body': body},
        }
    else:
        payload = {
            'registration_ids': tokens,
            'notification': {'title': title, 'body': body},
        }

    if data:
        payload['data'] = data

    headers = {
        'Authorization': f'key={settings.FCM_SERVER_KEY}',
        'Content-Type': 'application/json',
    }

    resp = requests.post(FCM_LEGACY_URL, json=payload, headers=headers, timeout=10)
    try:
        return resp.json()
    except Exception:
        return {'status_code': resp.status_code, 'text': resp.text}
