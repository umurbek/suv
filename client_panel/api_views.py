from rest_framework import viewsets, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from suv_tashish_crm.models import Order
from .serializers import OrderSerializer
from rest_framework.views import APIView
from rest_framework import status
from .models import PushToken


class RegisterPushToken(APIView):
    """Endpoint to register/update a device FCM token from the mobile app."""
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        token = request.data.get('token') or request.data.get('fcm_token')
        client_id = request.data.get('client_id') or request.data.get('user_id')
        platform = request.data.get('platform')
        if not token:
            return Response({'detail': 'token required'}, status=status.HTTP_400_BAD_REQUEST)

        obj, created = PushToken.objects.get_or_create(token=token, defaults={'client_id': client_id, 'platform': platform})
        if not created:
            changed = False
            if client_id and obj.client_id != client_id:
                obj.client_id = client_id
                changed = True
            if platform and obj.platform != platform:
                obj.platform = platform
                changed = True
            if changed:
                obj.save()

        return Response({'status': 'ok', 'created': created})


class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only API for client orders. Requires authentication."""
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # For API usage, client should authenticate and we expect a query param ?client_id=...
        client_id = self.request.query_params.get('client_id')
        qs = Order.objects.select_related('client').all().order_by('-created_at')
        if client_id:
            qs = qs.filter(client_id=client_id)
        return qs

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def my(self, request):
        """Shortcut to get orders for the provided client_id parameter."""
        client_id = request.query_params.get('client_id')
        if not client_id:
            return Response({'detail': 'client_id required as query param'}, status=400)
        qs = self.get_queryset().filter(client_id=client_id)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)
