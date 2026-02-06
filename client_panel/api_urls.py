from django.urls import path, include
from rest_framework import routers
from .api_views import OrderViewSet
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from .api_views import RegisterPushToken

router = routers.DefaultRouter()
router.register(r'orders', OrderViewSet, basename='orders')

urlpatterns = [
    path('', include(router.urls)),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('register_push_token/', RegisterPushToken.as_view(), name='register_push_token'),
    # (send/verify OTP endpoints removed temporarily)
]
