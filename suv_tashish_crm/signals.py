import os
import requests
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Admin, Courier, Client


def _get_telegram_config():
    # Prefer environment variables, fall back to Django settings if present
    token = os.environ.get('TELEGRAM_BOT_TOKEN') or getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
    chat = os.environ.get('TELEGRAM_CHAT_ID') or getattr(settings, 'TELEGRAM_CHAT_ID', None)
    return token, chat


def send_telegram_message(text):
    token, chat = _get_telegram_config()
    if not token or not chat:
        # Telegram not configured — do nothing (or print for dev)
        try:
            print('[telegram] not configured, message skipped:', text)
        except Exception:
            pass
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        resp = requests.post(url, data={'chat_id': chat, 'text': text})
        resp.raise_for_status()
    except Exception as e:
        try:
            print('Failed to send telegram message:', e)
        except Exception:
            pass


@receiver(post_save, sender=Admin)
def admin_created(sender, instance, created, **kwargs):
    if not created:
        return
    name = getattr(instance, 'full_name', '')
    phone = getattr(instance, 'phone', '')
    text = f"🛡️ Yangi Admin qo'shildi\nIsm: {name}\nTelefon: {phone}"
    send_telegram_message(text)


@receiver(post_save, sender=Courier)
def courier_created(sender, instance, created, **kwargs):
    if not created:
        return
    name = getattr(instance, 'full_name', '')
    phone = getattr(instance, 'phone', '')
    region = getattr(instance, 'region', None)
    region_name = region.name if region else ''
    text = f"🚚 Yangi Kuryer qo'shildi\nIsm: {name}\nTelefon: {phone}\nHudud: {region_name}"
    send_telegram_message(text)


@receiver(post_save, sender=Client)
def client_created(sender, instance, created, **kwargs):
    if not created:
        return
    name = getattr(instance, 'full_name', '')
    phone = getattr(instance, 'phone', '')
    cid = getattr(instance, 'customer_id', '')
    region = getattr(instance, 'region', None)
    region_name = region.name if region else ''
    text = f"👤 Yangi Mijoz qo'shildi\nIsm: {name}\nTelefon: {phone}\nID: {cid}\nHudud: {region_name}"
    send_telegram_message(text)
