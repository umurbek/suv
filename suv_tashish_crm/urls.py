from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from . import views

urlpatterns = [
    # Show login page by default; user must login to reach their dashboard
    path('', lambda request: redirect('/login/')),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    # login/logout removed per request
    path('admin/', admin.site.urls),
    path('admin_panel/', include('admin_panel.urls')),
    path('courier_panel/', include('courier_panel.urls')),
    path('client_panel/', include('client_panel.urls')),
    # API endpoints for client_panel (REST)
    path('api/client_panel/', include('client_panel.api_urls')),
]
