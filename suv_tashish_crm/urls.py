from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from . import views

urlpatterns = [
    # Default -> choose language first, then login
    path('', views.choose_language, name='choose_language'),

    # Auth
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('set_language/', views.set_language, name='set_language'),
    path('change_language/', views.change_language, name='change_language'),
    path('logout/', views.logout_view, name='logout'),

    # Django admin (FAKAT 1 MARTA)
    path('admin/', admin.site.urls),

    # Panels (namespace bilan)
    path('admin_panel/', include(('admin_panel.urls', 'admin_panel'), namespace='admin_panel')),
    path('courier_panel/', include(('courier_panel.urls', 'courier_panel'), namespace='courier_panel')),
    path('client_panel/', include(('client_panel.urls', 'client_panel'), namespace='client_panel')),

    # API
    path('api/', include('api.urls')),
    
]
