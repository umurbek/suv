from rest_framework import serializers
from suv_tashish_crm.models import Order, Client


class ClientBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = ('id', 'full_name', 'phone', 'customer_id')


class OrderSerializer(serializers.ModelSerializer):
    client = ClientBriefSerializer(read_only=True)

    class Meta:
        model = Order
        fields = ('id', 'client', 'courier_id', 'created_at', 'delivered_at', 'status', 'bottle_count', 'debt_change', 'client_note')
        read_only_fields = ('id', 'created_at', 'delivered_at')


class OrderCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ('bottle_count', 'client_note')

    def create(self, validated_data):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        # Expecting Django User.username to be phone number mapped to Client
        client = None
        if user and user.is_authenticated:
            from suv_tashish_crm.models import Client
            client = Client.objects.filter(phone=user.username).first()
        if not client:
            raise serializers.ValidationError('Authenticated client not found')

        order = Order.objects.create(
            client=client,
            bottle_count=validated_data.get('bottle_count', 0),
            client_note=validated_data.get('client_note', ''),
        )
        return order
