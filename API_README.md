Mobile API (quick reference)

Base URL example (on LAN): http://192.168.241.174:8000/

1) Create order (mobile-friendly JSON)

POST /client_panel/api/create_order/
Content-Type: application/json

Body example:
{
  "name": "Test User",
  "phone": "+998901112233",
  "bottles": 2,
  "note": "Leave at door",
  "lat": 41.2995,
  "lon": 69.2401
}

Response example:
{
  "status": "ok",
  "order_id": 123
}

Notes:
- Endpoint accepts both form-encoded POST (from web) and JSON POST (from mobile).
- If phone matches an existing client, order will be attached to that client; otherwise a new client record is created.
- For mobile apps using JWT authentication, use the token endpoints under `/client_panel/api/token/` (TokenObtainPairView) and send `Authorization: Bearer <access>` header on protected endpoints.

2) Register device FCM token

POST /client_panel/api/register_push_token/
Content-Type: application/json
Body example:
{
  "token": "<fcm_token>",
  "client_id": 12,
  "platform": "android"
}

3) Get JWT token

POST /client_panel/api/token/
Body (JSON): {"username": "...", "password": "..."}
Response: {"access": "...", "refresh": "..."}

Testing with curl (JSON create order):

curl -X POST "http://192.168.241.174:8000/client_panel/api/create_order/" \
  -H "Content-Type: application/json" \
  -d '{"name":"Test","phone":"+998901112233","bottles":1,"note":"curl test"}'

