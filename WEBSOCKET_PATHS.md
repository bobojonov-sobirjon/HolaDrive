# WebSocket Paths for Real-Time Notifications and Chat

## Overview
This document describes all WebSocket paths for real-time communication in the HoloDrive application.

## Base Configuration

**WebSocket Host/Port:**
- Default: `127.0.0.1:9000`
- Configurable via environment variables:
  - `WEBSOCKET_HOST` (default: `127.0.0.1`)
  - `WEBSOCKET_PORT` (default: `9000`)
  - `WEBSOCKET_URL` (default: `{WEBSOCKET_HOST}:{WEBSOCKET_PORT}`)

**Protocol:**
- Development: `ws://`
- Production (HTTPS): `wss://`

---

## 1. Real-Time Notifications WebSocket

### Path Pattern
```
ws://{WEBSOCKET_URL}/ws/notifications/
```

### Description
Real-time notifications for any user (Admin, Rider, or Driver). **User ID is automatically extracted from JWT token or session**, so it's not needed in the path.

### Authentication
- **Admin Panel**: Session-based authentication (automatic) - user is extracted from Django session
- **Mobile App**: JWT token in query string or URL path - user is extracted from JWT token
  - Query string: `?token=YOUR_JWT_TOKEN`
  - URL path: `/ws/notifications/YOUR_JWT_TOKEN` or `/ws/notifications/token=YOUR_JWT_TOKEN`

### Examples

#### For Admin Panel (Session Authentication)
```
ws://127.0.0.1:9000/ws/notifications/
```
*User is automatically extracted from Django session*

#### For Rider (JWT Token in Query String)
```
ws://127.0.0.1:9000/ws/notifications/?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

#### For Driver (JWT Token in URL Path)
```
ws://127.0.0.1:9000/ws/notifications/eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Message Format

#### Connection Established
```json
{
  "type": "connection_established",
  "message": "Connected to notifications",
  "user_id": "1"
}
```

#### Notification Received
```json
{
  "type": "notification",
  "notification": {
    "id": 38,
    "title": "New message from Sobirjon Bobojonov",
    "message": "New message in conversation: ashjkdbasljkdhgbasd...",
    "notification_type": "chat_message",
    "related_object_type": "conversation",
    "related_object_id": 1,
    "data": {
      "conversation_id": 1,
      "message_id": 38
    },
    "created_at": "2025-11-22T13:15:22.970153+00:00",
    "status": "unread"
  }
}
```

### Sending Messages (Mark as Read)
```json
{
  "type": "mark_as_read",
  "notification_id": 38
}
```

---

## 2. Real-Time Chat WebSocket

### Path Pattern
```
ws://{WEBSOCKET_URL}/ws/chat/{conversation_id}/
```

### Description
Real-time chat messages for a specific conversation.

### Parameters
- `{conversation_id}`: The ID of the conversation

### Authentication
- **Admin Panel**: Session-based authentication (automatic)
- **Mobile App**: JWT token in query string or URL path
  - Query string: `?token=YOUR_JWT_TOKEN`
  - URL path: `/ws/chat/{conversation_id}/YOUR_JWT_TOKEN`

### Examples

#### For Admin Panel
```
ws://127.0.0.1:9000/ws/chat/1/
```

#### For Mobile App (Rider/Driver)
```
ws://127.0.0.1:9000/ws/chat/1/?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Message Format

#### Connection Established
```json
{
  "type": "connection_established",
  "message": "Connected to chat",
  "conversation_id": 1
}
```

#### Send Message
```json
{
  "type": "chat_message",
  "message": "Hello, how can I help you?"
}
```

#### Receive Message
```json
{
  "type": "chat_message",
  "message": "Hello, how can I help you?",
  "sender_id": 2,
  "sender_name": "Sobirjon Bobojonov",
  "is_from_support": false,
  "created_at": "2025-11-22T13:15:22.970153+00:00",
  "message_id": 38
}
```

#### Typing Indicator
```json
{
  "type": "typing",
  "is_typing": true
}
```

---

## 3. Complete Examples

### Admin Panel - Notification Connection
```javascript
// In Django admin (base_site.html)
// User is automatically extracted from Django session
const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const websocketHost = window.websocketUrl || window.location.host;
const wsUrl = `${protocol}//${websocketHost}/ws/notifications/`;

const notificationSocket = new WebSocket(wsUrl);
```

### Mobile App (Rider/Driver) - Notification Connection
```javascript
// In mobile app
// User ID is automatically extracted from JWT token, no need to specify in path
const jwt_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."; // JWT token

// Option 1: Token in query string (Recommended)
const wsUrl = `ws://127.0.0.1:9000/ws/notifications/?token=${jwt_token}`;

// Option 2: Token in URL path
const wsUrl = `ws://127.0.0.1:9000/ws/notifications/${jwt_token}`;

// Option 3: Token in URL path with prefix
const wsUrl = `ws://127.0.0.1:9000/ws/notifications/token=${jwt_token}`;

const notificationSocket = new WebSocket(wsUrl);
```

### Mobile App (Rider/Driver) - Chat Connection
```javascript
// In mobile app
const conversation_id = 1;
const jwt_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."; // JWT token

// Option 1: Token in query string
const wsUrl = `ws://127.0.0.1:9000/ws/chat/${conversation_id}/?token=${jwt_token}`;

// Option 2: Token in URL path
const wsUrl = `ws://127.0.0.1:9000/ws/chat/${conversation_id}/${jwt_token}`;

const chatSocket = new WebSocket(wsUrl);
```

---

## 4. Summary Table

| Use Case | Path | Authentication | User Type |
|----------|------|----------------|-----------|
| Admin Notifications | `/ws/notifications/` | Session (auto) | Admin |
| Rider Notifications | `/ws/notifications/?token={jwt}` | JWT Token | Rider |
| Driver Notifications | `/ws/notifications/?token={jwt}` | JWT Token | Driver |
| Admin Chat | `/ws/chat/{conversation_id}/` | Session | Admin |
| Rider Chat | `/ws/chat/{conversation_id}/?token={jwt}` | JWT Token | Rider |
| Driver Chat | `/ws/chat/{conversation_id}/?token={jwt}` | JWT Token | Driver |

---

## 5. Testing with Postman

### Connect to Notifications
1. Open Postman
2. Create a new WebSocket request
3. URL: `ws://127.0.0.1:9000/ws/notifications/?token=YOUR_JWT_TOKEN`
   - Or: `ws://127.0.0.1:9000/ws/notifications/YOUR_JWT_TOKEN`
4. Click "Connect"

### Connect to Chat
1. Open Postman
2. Create a new WebSocket request
3. URL: `ws://127.0.0.1:9000/ws/chat/1/?token=YOUR_JWT_TOKEN`
4. Click "Connect"
5. Send message:
```json
{
  "type": "chat_message",
  "message": "Hello from Postman!"
}
```

---

## 6. Notes

1. **User ID Extraction**: User ID is automatically extracted from:
   - **Admin Panel**: Django session (no token needed)
   - **Mobile App**: JWT token (user_id is in the token payload)
   
   **No need to specify user_id in the path!**

2. **Token Authentication**: For mobile apps, JWT tokens can be provided either:
   - As a query parameter: `?token=YOUR_TOKEN`
   - In the URL path: `/ws/notifications/{user_id}/YOUR_TOKEN`

3. **Session Authentication**: Admin panel uses Django session authentication automatically.

4. **Reconnection**: If the connection is lost, clients should implement automatic reconnection logic.

5. **Error Handling**: Always handle WebSocket errors and connection close events in your client code.

---

## 7. Environment Variables

Add to your `.env` file:
```env
WEBSOCKET_HOST=127.0.0.1
WEBSOCKET_PORT=9000
WEBSOCKET_URL=127.0.0.1:9000
```

For production:
```env
WEBSOCKET_HOST=your-domain.com
WEBSOCKET_PORT=9000
WEBSOCKET_URL=your-domain.com:9000
```

