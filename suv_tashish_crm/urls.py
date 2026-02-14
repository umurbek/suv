from django.contrib import admin
from django.urls import path, include
from . import views

# API viewlarini import qilish (export funksiyasi uchun)
from api.views import admin_orders_view #

urlpatterns = [
    # Tilni tanlash va Auth
    path('', views.choose_language, name='choose_language'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('set_language/', views.set_language, name='set_language'),
    path('change_language/', views.change_language, name='change_language'),
    path('logout/', views.logout_view, name='logout'),

    # Django admin
    path('admin/', admin.site.urls),

    # Panellar (namespace bilan)
    path('admin_panel/', include(('admin_panel.urls', 'admin_panel'), namespace='admin_panel')),
    path('courier_panel/', include(('courier_panel.urls', 'courier_panel'), namespace='courier_panel')),
    path('client_panel/', include(('client_panel.urls', 'client_panel'), namespace='client_panel')),

    # Excel export (Xatolik tuzatilgan joy)
    path("admin/export/clients/excel/", admin_orders_view, name="export_admin_clients_excel"), #

    # API ulanishi
    path('api/', include('api.urls')),
]