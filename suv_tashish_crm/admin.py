from django.contrib import admin
from .models import Admin as SiteAdmin, Courier, Client, Region, Notification, Order, BottleHistory, DebtHistory

# Customize admin site header
admin.site.site_header = "Suv Tashish CRM Admin"
admin.site.site_title = "SuvCRM Admin"
admin.site.index_title = "Sayt ma'muriyati"


@admin.register(SiteAdmin)
class SiteAdminAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'phone', 'telegram_id')
    search_fields = ('full_name', 'phone')


@admin.register(Courier)
class CourierAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'phone', 'region', 'is_active')
    list_filter = ('is_active', 'region')
    search_fields = ('full_name', 'phone')


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'phone', 'customer_id', 'region', 'bottle_balance', 'debt', 'last_order')
    search_fields = ('full_name', 'phone', 'customer_id')
    list_filter = ('region',)


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_at', 'seen')
    list_filter = ('seen',)
    search_fields = ('title', 'message')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'client', 'courier', 'status', 'bottle_count', 'created_at', 'delivered_at')
    list_filter = ('status',)
    search_fields = ('client__full_name', 'client__phone')
    raw_id_fields = ('client', 'courier')

    @admin.display(description="Bottles")
    def bottle_count(self, obj):
        # Order modelida field nomi: bottles
        return obj.bottles


@admin.register(BottleHistory)
class BottleHistoryAdmin(admin.ModelAdmin):
    list_display = ('client', 'change', 'created_at')
    search_fields = ('client__full_name',)


@admin.register(DebtHistory)
class DebtHistoryAdmin(admin.ModelAdmin):
    list_display = ('client', 'change', 'created_at')
    search_fields = ('client__full_name',)