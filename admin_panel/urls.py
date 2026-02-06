from django.urls import path
from . import views
from .import_csv import import_clients_ui

app_name = "admin_panel"

urlpatterns = [
    # Dashboard
    path("dashboard/", views.admin_dashboard, name="admin_dashboard"),

    # Regions
    path("regions/", views.regions_view, name="regions_view"),
    path("regions/add/", views.add_region, name="add_region"),
    path("regions/update/", views.update_region, name="update_region"),
    path("regions/delete/", views.delete_region, name="delete_region"),
    path("regions/clients/", views.region_clients_api, name="region_clients_api"),

    # Couriers
    path("couriers/", views.couriers_view, name="couriers_view"),
    path("couriers/add/", views.add_courier, name="add_courier"),
    path("couriers/<int:courier_id>/edit/", views.edit_courier, name="edit_courier"),
    path("couriers/<int:courier_id>/delete/", views.delete_courier, name="delete_courier"),

    # Clients (ADMIN)
    path("clients/", views.clients_list, name="clients_list"),            # ✅ list
    path("clients/add/", views.add_client, name="add_client"),
    path("clients/import/", import_clients_ui, name="clients_import"),
    # path("clients/export_excel/", views.export_admin_clients_excel, name="export_admin_clients_excel"),
    path("clients/<int:client_id>/edit/", views.edit_client, name="edit_client"),
    path("clients/<int:client_id>/delete/", views.delete_client, name="delete_client"),

    # Inactive clients
    path("inactive/10days/", views.inactive_clients_view, name="inactive_10days"),

    # Orders
    path("orders/", views.orders_view, name="orders_view"),
    path("orders/<int:order_id>/delete/", views.delete_order, name="delete_order"),
    path("orders/seed/", views.seed_region_orders, name="seed_region_orders"),

    # Notifications
    path("notifications/", views.notifications_api, name="notifications_api"),

    # Reports
    path("reports/", views.reports_view, name="reports_view"),
    path("reports/financial/", views.reports_view, name="financial_reports"),

    # Courier ranking (FAKAT 1 MARTA)
    path("courier_ranking/", views.courier_ranking_view, name="courier_ranking"),

    # Debtors
    path("debtors/", views.debtors_view, name="debtors_view"),
    path("debtors/<int:client_id>/paid/", views.mark_debtor_paid, name="mark_debtor_paid"),

    # Admin Profile
    path("profile/", views.profile_view, name="admin_profile"),
    path("api/update_profile/", views.api_update_profile, name="admin_update_profile"),
 
    path("clients/upload-excel/", views.admin_clients_upload_excel, name="clients_upload_excel"),
    # path("clients/export-excel/", views.admin_clients_export_excel, name="clients_export_excel"),
    path("clients/export/", views.admin_clients_export_excel, name="clients_export_excel"),

    





]
