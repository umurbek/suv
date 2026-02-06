from django.contrib import admin
from .models import AdminProfile

@admin.register(AdminProfile)
class AdminProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'full_name', 'user', 'role', 'created_at')
    search_fields = ('full_name', 'user__username')