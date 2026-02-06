from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser

from .views import get_role
from .import_utils import read_table_upload, import_clients, import_couriers


def _require_admin(request):
    if get_role(request.user) != "ADMIN":
        return Response({"detail": "FORBIDDEN"}, status=403)
    return None


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def admin_import_clients_view(request):
    forbidden = _require_admin(request)
    if forbidden:
        return forbidden

    f = request.FILES.get("file")
    if not f:
        return Response({"detail": "NO_FILE"}, status=400)

    default_password = (request.data.get("default_password") or "").strip()
    if not default_password:
        return Response({"detail": "NO_DEFAULT_PASSWORD"}, status=400)

    mode = (request.data.get("mode") or "upsert").strip().lower()
    if mode not in ("upsert", "create_only"):
        mode = "upsert"

    try:
        rows, filetype = read_table_upload(f)
    except ValueError as e:
        return Response({"detail": str(e)}, status=400)

    res = import_clients(rows, default_password=default_password, mode=mode)
    return Response({
        "filetype": filetype,
        "total": res.total,
        "created": res.created,
        "updated": res.updated,
        "skipped": res.skipped,
        "errors": res.errors,
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def admin_import_couriers_view(request):
    forbidden = _require_admin(request)
    if forbidden:
        return forbidden

    f = request.FILES.get("file")
    if not f:
        return Response({"detail": "NO_FILE"}, status=400)

    default_password = (request.data.get("default_password") or "").strip()
    if not default_password:
        return Response({"detail": "NO_DEFAULT_PASSWORD"}, status=400)

    mode = (request.data.get("mode") or "upsert").strip().lower()
    if mode not in ("upsert", "create_only"):
        mode = "upsert"

    try:
        rows, filetype = read_table_upload(f)
    except ValueError as e:
        return Response({"detail": str(e)}, status=400)

    res = import_couriers(rows, default_password=default_password, mode=mode)
    return Response({
        "filetype": filetype,
        "total": res.total,
        "created": res.created,
        "updated": res.updated,
        "skipped": res.skipped,
        "errors": res.errors,
    })
