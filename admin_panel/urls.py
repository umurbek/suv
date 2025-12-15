from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('regions/', views.regions_view, name='regions_view'),
    path('regions/add/', views.add_region, name='add_region'),
    path('regions/update/', views.update_region, name='update_region'),
    path('regions/clients/', views.region_clients_api, name='region_clients_api'),
    path('regions/delete/', views.delete_region, name='delete_region'),
    path('couriers/', views.couriers_view, name='couriers_view'),
    path('couriers/add/', views.add_courier, name='add_courier'),
    path('couriers/<int:courier_id>/edit/', views.edit_courier, name='edit_courier'),
    path('couriers/<int:courier_id>/delete/', views.delete_courier, name='delete_courier'),
    path('customers/', views.clients_view, name='clients_view'),
    path('orders/', views.orders_view, name='orders_view'),
    path('orders/seed/', views.seed_region_orders, name='seed_region_orders'),
    path('notifications/', views.notifications_api, name='notifications_api'),
    path('reports/financial/', views.reports_view, name='financial_reports'),
    path('clients/<int:client_id>/edit/', views.edit_client, name='edit_client'),
    path('clients/<int:client_id>/delete/', views.delete_client, name='delete_client'),
    path('reports/', views.reports_view, name='reports_view'),
    path('debtors/', views.debtors_view, name='debtors_view'),
    path('debtors/<int:client_id>/paid/', views.mark_debtor_paid, name='mark_debtor_paid'),
    path('inactive/10days/', views.inactive_clients_view, name='inactive_10days'),
]
