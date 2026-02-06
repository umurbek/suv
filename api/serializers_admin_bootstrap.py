# api/serializers_admin_bootstrap.py
from rest_framework import serializers


class AdminBootstrapRequestSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=255)
    phone = serializers.CharField(max_length=32)
    email = serializers.EmailField()
    company_key = serializers.CharField(required=False, allow_blank=True)


class AdminBootstrapVerifySerializer(serializers.Serializer):
    request_id = serializers.IntegerField()
    code = serializers.CharField(min_length=6, max_length=6)


class AdminBootstrapCompleteSerializer(serializers.Serializer):
    request_id = serializers.IntegerField()
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(min_length=6, max_length=128)