import os
import requests
from datetime import datetime
from django.conf import settings


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_PATH = os.path.join(BASE_DIR, 'telegram_debug.log')


def send_telegram(text: str, bot_token: str = None, chat_id: str = None, silent: bool = True) -> bool:
    """Send `text` to configured Telegram bot/chat. Logs results to `telegram_debug.log`.

    Returns True on success, False otherwise. Errors are logged and swallowed unless `silent` is False.
    """
    try:
        if bot_token is None:
            bot_token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
        if chat_id is None:
            chat_id = getattr(settings, 'TELEGRAM_CHAT_ID', None)
        if not bot_token or not chat_id:
            if not silent:
                print('Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID in settings')
            _log(f'MISSING_CONFIG text={text!r}')
            return False

        url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
        payload = {'chat_id': chat_id, 'text': text}
        resp = requests.post(url, json=payload, timeout=10)
        ok = False
        try:
            j = resp.json()
            ok = j.get('ok', False)
        except Exception:
            ok = resp.status_code == 200

        _log(f'SEND text={text!r} status={resp.status_code} ok={ok} resp={resp.text!r}')
        return ok
    except Exception as e:
        _log(f'EXCEPTION sending text={text!r} error={e!s}')
        if not silent:
            raise
        return False


def _log(msg: str) -> None:
    try:
        with open(LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(f'[{datetime.utcnow().isoformat()}] {msg}\n')
    except Exception:
        # Best-effort logging only
        pass
