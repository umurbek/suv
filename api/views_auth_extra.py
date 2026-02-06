from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .views import get_role
from suv_tashish_crm.models import Client, Courier


def _set_flag_false(user):
    role = get_role(user)
    if role == "CLIENT":
        c = Client.objects.filter(user=user).first()
        if c:
            c.must_change_password = False
            c.save(update_fields=["must_change_password"])
    elif role == "COURIER":
        q = Courier.objects.filter(user=user).first()
        if q:
            q.must_change_password = False
            q.save(update_fields=["must_change_password"])


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def change_password_view(request):
    new_password = (request.data.get("new_password") or "").strip()
    if len(new_password) < 6:
        return Response({"detail": "PASSWORD_TOO_SHORT"}, status=400)

    u = request.user
    u.set_password(new_password)
    u.save()
    _set_flag_false(u)
    return Response({"ok": True})
