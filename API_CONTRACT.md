# TaskFlow API Contract & Conventions

> **Target audience:** Frontend developers & API consumers.  
> **API Version:** v1 (`/api/v1`)  
> **Swagger UI:** `http://localhost:8000/api/docs`  
> **ReDoc:** `http://localhost:8000/api/redoc`  
> **OpenAPI JSON:** `http://localhost:8000/openapi.json`

---

## 1. General Principles

1. **Protocol:** HTTP/1.1 and HTTP/2 over TLS (production) / Plain HTTP (local dev).
2. **Base URL:**
   - Local: `http://localhost:8000/api/v1`
   - WebSocket: `ws://localhost:8000/api/v1/ws/notifications`
3. **Data format:** JSON (`application/json; charset=utf-8`) for all requests & responses, except file uploads (`multipart/form-data`).
4. **Timezone:** All timestamps are ISO 8601 in UTC (`YYYY-MM-DDTHH:MM:SSZ` or `YYYY-MM-DDTHH:MM:SS+00:00`).
5. **Soft-deleted entities:** Return `404 Not Found` when accessed directly by ID.

---

## 2. Authentication & Authorization

All protected endpoints require an `Authorization` header with a Bearer token:
```http
Authorization: Bearer <access_token>
```

- **Access Token:** Short-lived JWT (15 minutes).
- **Refresh Token:** Opaque string (30 days), single-use with automatic rotation.
- **Revocation / Logout:** When logging out, the refresh token is deleted from the DB and the access token's unique ID (`jti`) is added to the Redis blacklist until its expiration.

---

## 3. Standard Error Envelope

Every 4xx and 5xx response strictly follows this uniform JSON structure:

```json
{
  "error": {
    "code": "ERROR_CODE_STRING",
    "message": "Human-readable explanation for debugging or display.",
    "details": null
  }
}
```

### Common Error Codes

| HTTP Status | Error Code | Description / Context |
|---|---|---|
| `400 Bad Request` | `INVALID_REQUEST` | Malformed request parameters or invalid payload. |
| `401 Unauthorized` | `AUTHENTICATION_FAILED` | Invalid credentials or missing Authorization header. |
| `401 Unauthorized` | `TOKEN_EXPIRED` | The access token has expired. Send refresh token to `/auth/refresh`. |
| `401 Unauthorized` | `TOKEN_REVOKED` | The token was revoked via logout or password change. |
| `401 Unauthorized` | `TOKEN_INVALID` | Malformed or forged JWT signature. |
| `403 Forbidden` | `PERMISSION_DENIED` | Role insufficient to perform the action. |
| `404 Not Found` | `NOT_FOUND` | Resource does not exist (or belongs to another workspace). |
| `409 Conflict` | `ALREADY_EXISTS` | Unique constraint violated (e.g. duplicate email/username/slug). |
| `409 Conflict` | `VERSION_CONFLICT` | Task was modified concurrently by another user. |
| `409 Conflict` | `TIMER_ALREADY_RUNNING` | User already has an active running timer. |
| `409 Conflict` | `LAST_OWNER` | Cannot remove or demote the last remaining owner in workspace. |
| `422 Unprocessable` | `VALIDATION_ERROR` | Schema validation error (e.g. weak password, bad field length). |
| `422 Unprocessable` | `CYCLIC_DEPENDENCY` | Setting task parent creates an infinite circular tree. |
| `429 Too Many Requests` | `RATE_LIMIT_EXCEEDED` | Request rate limit exceeded. Retry later. |
| `500 Server Error` | `INTERNAL_ERROR` | Unhandled server error. |

---

## 4. Pagination & Filtering

List endpoints adhere to the standard paginated envelope:

```json
{
  "items": [ ... ],
  "total": 128,
  "limit": 20,
  "offset": 0,
  "has_next": true
}
```

- Query parameters:
  - `limit`: Integer, default `20`, max `100`.
  - `offset`: Integer, default `0`.

---

## 5. Optimistic Concurrency Control

When updating tasks via `PATCH /tasks/{id}`, send the current `version`:

```json
{
  "title": "Updated task title",
  "version": 2
}
```

If another user has edited the task in the meantime, the server returns `409 Conflict` with `code: "VERSION_CONFLICT"`. The frontend should reload the task state and ask the user to resolve or reapply changes.

---

## 6. WebSocket Protocol

Connect to:
```
ws://localhost:8000/api/v1/ws/notifications?token=<access_token>
```

### Server-to-Client Events

1. **New Notification:**
```json
{
  "event": "notification.new",
  "payload": {
    "id": "c7117e3c-8480-4cf8-8c10-38e21974ef43",
    "type": "MENTION",
    "entity_type": "task",
    "entity_id": "0d6e6761-fae6-42bc-a27d-944a30ff13c7",
    "message": "Alice assigned you to task 'Implement WebSocket notification stream'",
    "created_at": "2026-10-18T12:00:00Z"
  }
}
```

2. **Heartbeat / Ping:**
```json
{
  "event": "ping"
}
```

### Client-to-Server Events

1. **Mark Notification Read:**
```json
{
  "event": "mark_read",
  "payload": {
    "notification_id": "c7117e3c-8480-4cf8-8c10-38e21974ef43"
  }
}
```

2. **Heartbeat / Pong:**
```json
{
  "event": "pong"
}
```
