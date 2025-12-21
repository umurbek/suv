from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard, name='courier_dashboard'),
    # API endpoints for dashboard (polled by frontend)
    path('api/today_orders/', views.api_today_orders, name='courier_api_today_orders'),
    path('api/weekly_stats/', views.api_weekly_stats, name='courier_api_weekly_stats'),
    path('api/history/', views.api_history, name='courier_api_history'),
    path('api/debtors/', views.api_debtors, name='courier_api_debtors'),
    path('api/inactive_clients/', views.api_inactive_clients, name='courier_api_inactive_clients'),
    path('api/position/', views.api_get_position, name='courier_api_get_position'),
    path('api/metrics/', views.api_metrics, name='courier_api_metrics'),
    path('api/update_position/', views.api_update_position, name='courier_api_update_position'),
    # Dev helper to set session courier_id for simulation/testing
    path('dev/set_session/<int:courier_id>/', views.dev_set_session, name='courier_dev_set_session'),
    path('contact_admin/', views.contact_admin, name='courier_contact_admin'),
    path('dev/login_as/<int:courier_id>/', views.dev_login_as, name='courier_dev_login_as'),
    # New orders & accept endpoints
    path('api/new_orders/', views.api_new_orders, name='courier_api_new_orders'),
    path('api/accept_order/', views.api_accept_order, name='courier_api_accept_order'),
    path('api/confirm_delivery/', views.api_confirm_delivery, name='courier_api_confirm_delivery'),
    path('api/create_order_by_courier/', views.api_create_order_by_courier, name='courier_api_create_order_by_courier'),
    # Dedicated pages for courier
    path('new_orders/', views.new_orders_page, name='courier_new_orders_page'),
    path('history/', views.history_page, name='courier_history_page'),
]