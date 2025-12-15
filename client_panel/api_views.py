from rest_framework import viewsets, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from suv_tashish_crm.models import Order
from .serializers import OrderSerializer


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
