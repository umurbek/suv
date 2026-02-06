from django.urls import path
from . import views
from django.urls import path
from api.views import me_view
app_name = 'client_panel'   # 👈 MUHIM QATOR

urlpatterns = [
    path("api/me/", me_view),
    path('dashboard/', views.dashboard, name='client_dashboard'),
    path('contract/', views.contract_view, name='client_contract'),
    path('profile/', views.profile_view, name='client_profile'),
    path('orders/', views.orders_view, name='client_orders'),
    path('contact_admin/', views.contact_admin, name='client_contact_admin'),

    # API endpoints
    path('api/orders/', views.api_client_orders, name='client_api_orders'),
    path('api/update_profile/', views.api_update_profile, name='api_update_profile'),
    path('api/create_order/', views.api_create_order, name='api_create_order'),
    path('api/contact_admin/', views.api_contact_admin, name='api_contact_admin'),

    # Dev helpers
    path('dev/set_session/<int:client_id>/', views.dev_set_session, name='client_dev_set_session'),
    path('dev/login_as/<int:client_id>/', views.dev_login_as, name='client_dev_login_as'),
]
