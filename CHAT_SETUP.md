# Real-Time Chat & Notification Setup Guide

## 📋 Overview

This project includes real-time chat functionality between Riders/Drivers and Support, along with real-time notifications using Django Channels and WebSockets.

## 🚀 Installation Steps

### 1. Install Required Packages

```bash
pip install -r requirements.txt
```

Key packages added:
- `channels==4.1.0` - Django Channels for WebSocket support
- `channels-redis==4.2.0` - Redis backend for Channels
- `redis==5.2.0` - Redis Python client

### 2. Install and Start Redis

#### Windows:
Download Redis from: https://github.com/microsoftarchive/redis/releases
Or use WSL:
```bash
wsl
sudo apt-get install redis-server
redis-server
```

#### Linux/Mac:
```bash
sudo apt-get install redis-server  # Ubuntu/Debian
brew install redis  # Mac
redis-server
```

#### Docker (Recommended):
```bash
docker run -d -p 6379:6379 redis:latest
```

### 3. Run Migrations

```bash
python manage.py migrate
```

### 4. Configuration

#### Development (Without Redis):
If you don't have Redis, you can use InMemoryChannelLayer for development. 
Edit `config/settings.py`:

```python
# For development without Redis
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer'
    },
}
```

#### Production (With Redis):
Make sure Redis is running and update `config/settings.py`:

```python
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [('127.0.0.1', 6379)],  # Redis server address
        },
    },
}
```

### 5. Run the Server

#### Development:
```bash
python manage.py runserver
```

#### Production (with ASGI):
```bash
daphne config.asgi:application --bind 0.0.0.0 --port 8000
```

Or use Gunicorn with Uvicorn workers:
```bash
gunicorn config.asgi:application -w 4 -k uvicorn.workers.UvicornWorker
```

## 📡 WebSocket Endpoints

### Chat WebSocket:
```
ws://localhost:8000/ws/chat/{conversation_id}/?token={jwt_token}
```

### Notification WebSocket:
```
ws://localhost:8000/ws/notifications/{user_id}/?token={jwt_token}
```

## 🔧 Models Created

### Chat App:
1. **Conversation** - Chat conversations between users and support
2. **Message** - Individual messages in conversations

### Notification App:
1. **Notification** - Real-time notifications for users

## 📝 Usage Example

### Frontend (JavaScript):
```javascript
// Connect to chat
const chatSocket = new WebSocket(
    'ws://localhost:8000/ws/chat/1/?token=your_jwt_token'
);

chatSocket.onmessage = function(e) {
    const data = JSON.parse(e.data);
    if (data.type === 'chat_message') {
        console.log('New message:', data.message);
    }
};

// Send message
chatSocket.send(JSON.stringify({
    type: 'chat_message',
    message: 'Hello, support!'
}));
```

## 🎯 Features

- ✅ Real-time chat between Riders/Drivers and Support
- ✅ Real-time notifications
- ✅ Typing indicators
- ✅ Message read receipts
- ✅ Unread message counts
- ✅ File attachments support
- ✅ Admin panel integration

## 🔒 Authentication

WebSocket connections require JWT token authentication. Pass the token as a query parameter:
```
?token=your_jwt_token
```

## 📚 Next Steps

1. Create API views for:
   - Creating conversations
   - Getting conversation list
   - Getting messages
   - Sending messages

2. Create frontend components for:
   - Chat interface
   - Notification center
   - Real-time updates

