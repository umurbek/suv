from django.urls import path
from .views import courier_order_track_view
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import client_create_order_view
from django.urls import path
from .views_admin_bootstrap import (
    AdminBootstrapRequestOTP,
    AdminBootstrapVerifyOTP,
    AdminBootstrapComplete,
)
from .views_auth_extra import change_password_view
from .views_import import admin_import_clients_view, admin_import_couriers_view
from .views import (
    check_status, me_view,

    # ADMIN
    admin_dashboard_view, admin_orders_view, admin_order_done_view,
    admin_couriers_view, admin_courier_toggle_view,
    admin_debtors_view, admin_debtor_paid_view,
    admin_profile_view, admin_notifications_view, admin_notification_seen_view,

    # COURIER
    courier_metrics_view,
    courier_today_orders_view,
    courier_position_view,
    courier_update_position_view,
    courier_accept_order_view,
    courier_confirm_delivery_view,
    courier_history_view,

    # CLIENT (DRF / JWT)
    client_me_view,
    client_metrics_view,
    client_recent_orders_view,
    client_create_order_view,

    # CLIENT PANEL (SESSION JSON)
    api_client_orders,
    api_update_profile,
    api_contact_admin,
    api_create_order,
    client_order_track_view,
    client_update_location_view,
    courier_start_delivery_view,
    admin_recovery_start_view,
    admin_recovery_verify_view,
    admin_recovery_set_credentials_view,
    admin_courier_create_view
)

urlpatterns = [
    # AUTH
    path("auth/jwt/login/", TokenObtainPairView.as_view(), name="jwt_login"),
    path("auth/jwt/refresh/", TokenRefreshView.as_view(), name="jwt_refresh"),
    path("auth/me/", me_view, name="me"),
    path("auth/change-password/", change_password_view, name="change_password"),
    path("check/", check_status, name="check_status"),

    # ADMIN
    path("admin/dashboard/", admin_dashboard_view, name="admin_dashboard"),
    path("admin/orders/", admin_orders_view, name="admin_orders"),
    path("admin/orders/<int:pk>/done/", admin_order_done_view, name="admin_order_done"),
    path("admin/couriers/", admin_couriers_view, name="admin_couriers"),
    path("admin/couriers/<int:pk>/toggle/", admin_courier_toggle_view, name="admin_courier_toggle"),
    path("admin/debtors/", admin_debtors_view, name="admin_debtors"),
    path("admin/debtors/<int:pk>/paid/", admin_debtor_paid_view, name="admin_debtor_paid"),
    path("admin/profile/", admin_profile_view, name="admin_profile"),
    path("admin/notifications/", admin_notifications_view, name="admin_notifications"),
    path("admin/notifications/<int:pk>/seen/", admin_notification_seen_view, name="admin_notification_seen"),

    # ADMIN IMPORT (CSV/XLSX)
    path("admin/import/clients/", admin_import_clients_view, name="admin_import_clients"),
    path("admin/import/couriers/", admin_import_couriers_view, name="admin_import_couriers"),


    # COURIER
    path("courier/metrics/", courier_metrics_view, name="courier_metrics"),
    path("courier/today_orders/", courier_today_orders_view, name="courier_today_orders"),
    path("courier/position/", courier_position_view, name="courier_position"),
    path("courier/update_position/", courier_update_position_view, name="courier_update_position"),
    path("courier/accept_order/", courier_accept_order_view, name="courier_accept_order"),
    path("courier/confirm_delivery/", courier_confirm_delivery_view, name="courier_confirm_delivery"),
    path("courier/history/", courier_history_view, name="courier_history"),

    # ✅ CLIENT (DRF / JWT) — siz urayotgan endpoint shu
    path("client/me/", client_me_view, name="client_me"),
    path("client/metrics/", client_metrics_view, name="client_metrics"),
    path("client/recent_orders/", client_recent_orders_view, name="client_recent_orders"),
    path("client/create_order/", client_create_order_view, name="client_create_order"),

    # CLIENT PANEL (SESSION JSON)
    path("client_panel/orders/", api_client_orders, name="client_panel_orders"),
    path("client_panel/profile/update/", api_update_profile, name="client_panel_update_profile"),
    path("client_panel/contact_admin/", api_contact_admin, name="client_panel_contact_admin"),
    path("client_panel/create_order/", api_create_order, name="client_panel_create_order"),
    path("client/order/<int:pk>/track/", client_order_track_view),
    path("client/update_location/", client_update_location_view, name="client_update_location"),
    path("courier/start_delivery/", courier_start_delivery_view, name="courier_start_delivery"),
    # AUTH
    path("auth/admin/start/", admin_recovery_start_view, name="admin_recovery_start"),
    path("auth/admin/verify/", admin_recovery_verify_view, name="admin_recovery_verify"),
    path("auth/admin/set_credentials/", admin_recovery_set_credentials_view, name="admin_recovery_set_credentials"),
    path("auth/admin/request-otp/", AdminBootstrapRequestOTP.as_view()),
    path("auth/admin/verify-otp/", AdminBootstrapVerifyOTP.as_view()),
    path("auth/admin/complete/", AdminBootstrapComplete.as_view()),
    # api/urls.py
    path("courier/order/<int:pk>/track/", courier_order_track_view, name="courier_order_track"),
    path("admin/couriers/create/", admin_courier_create_view, name="admin_courier_create"),

]