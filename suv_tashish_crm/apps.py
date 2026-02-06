from django.apps import AppConfig


class SuvTashishCrmConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "suv_tashish_crm"

    def ready(self):
        # Signal handlerlar ro‘yxatdan o‘tishi uchun import qilamiz
        import suv_tashish_crm.signals       # telegram + courier auto-link (signals.py ichida ham bor)
        import suv_tashish_crm.user_signals  # user -> courier auto-link