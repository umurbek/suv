from rest_framework import serializers
from suv_tashish_crm.models import Order

class OrderSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source='client.full_name', read_only=True)
    client_phone = serializers.CharField(source='client.phone', read_only=True)
    lat = serializers.FloatField(source='client.location_lat', read_only=True)
    lon = serializers.FloatField(source='client.location_lon', read_only=True)

    total_display = serializers.SerializerMethodField()

    def get_total_display(self, obj):
        amt = getattr(obj, "payment_amount", 0) or 0
        # 1 250 000 UZS ko‘rinishida
        return f"{int(amt):,} UZS".replace(",", " ")

    class Meta:
        model = Order
        fields = [
            'id', 'client_name', 'client_phone', 'status',
            'bottle_count', 'created_at', 'payment_amount',
            'lat', 'lon', 'total_display'
        ]
