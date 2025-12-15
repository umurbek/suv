from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard, name='client_dashboard'),
    path('profile/', views.profile_view, name='client_profile'),
    path('orders/', views.orders_view, name='client_orders'),
    path('contact_admin/', views.contact_admin, name='client_contact_admin'),
    path('api/update_profile/', views.api_update_profile, name='api_update_profile'),
    path('api/create_order/', views.api_create_order, name='api_create_order'),
    path('api/contact_admin/', views.api_contact_admin, name='api_contact_admin'),
    # Dev helpers for testing sessions
    path('dev/set_session/<int:client_id>/', views.dev_set_session, name='client_dev_set_session'),
    path('dev/login_as/<int:client_id>/', views.dev_login_as, name='client_dev_login_as'),
]