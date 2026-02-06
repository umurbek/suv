from django.contrib import admin
from suv_tashish_crm.models import PushToken
from .models import Order


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'status', 'bottles', 'lat', 'lon', 'created_at')
    list_editable = ('status',)
    list_filter = ('status', 'created_at')
    search_fields = ('id', 'note')
    date_hierarchy = 'created_at'

    fieldsets = (
        ("Asosiy ma'lumotlar", {
            'fields': ('status', 'bottles', 'note')
        }),
        ("Geolokatsiya (Kuryer uchun)", {
            'fields': ('lat', 'lon'),
            'description': 'Mijozning xaritadagi koordinatalari'
        }),
    )


@admin.register(PushToken)
class PushTokenAdmin(admin.ModelAdmin):
    list_display = ('token_short', 'user', 'platform', 'created_at')
    search_fields = ('token', 'user__username')
    list_filter = ('platform', 'created_at')

    def token_short(self, obj):
        return f"{obj.token[:30]}..."
    token_short.short_description = 'Token'
