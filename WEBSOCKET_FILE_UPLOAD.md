# WebSocket File Upload - Sender (Rider/Driver) uchun

## Postman orqali file yuborish

### 1. WebSocket Connection

**URL Format:**
```
ws://127.0.0.1:9000/ws/chat/{conversation_id}/token={JWT_TOKEN}
```

**Misol:**
```
ws://127.0.0.1:9000/ws/chat/1/token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### 2. Request Body Format

#### Text Message (faqat matn):
```json
{
    "type": "chat_message",
    "message": "Salom, bu test xabari"
}
```

#### File yuborish (base64):
```json
{
    "type": "chat_message",
    "message": "Bu rasm yuborilmoqda",
    "file_base64": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
    "file_name": "test_image.jpg",
    "file_type": "image"
}
```

#### Audio yuborish:
```json
{
    "type": "chat_message",
    "message": "Bu audio fayl",
    "file_base64": "UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA=",
    "file_name": "audio.mp3",
    "file_type": "audio"
}
```

#### Boshqa file yuborish:
```json
{
    "type": "chat_message",
    "message": "Bu document fayl",
    "file_base64": "JVBERi0xLjQKJeLjz9MKMy...",
    "file_name": "document.pdf",
    "file_type": "file"
}
```

### 3. File Type Values

- `"image"` - Rasm fayllar (jpg, png, gif, bmp, webp, svg)
- `"audio"` - Audio fayllar (mp3, wav, ogg, m4a, aac, flac)
- `"file"` - Boshqa barcha fayllar (pdf, doc, txt, va h.k.)

### 4. Base64 Encoding

**Python orqali base64 qilish:**
```python
import base64

# File o'qish
with open('image.jpg', 'rb') as f:
    file_data = f.read()

# Base64 ga o'tkazish
base64_string = base64.b64encode(file_data).decode('utf-8')

print(base64_string)
```

**JavaScript orqali base64 qilish:**
```javascript
// File input orqali
const fileInput = document.getElementById('fileInput');
const file = fileInput.files[0];

const reader = new FileReader();
reader.onload = function(e) {
    const base64 = e.target.result;
    // "data:image/jpeg;base64," prefix ni olib tashlash kerak
    const base64String = base64.split(',')[1];
    console.log(base64String);
};
reader.readAsDataURL(file);
```

### 5. Postman Setup

1. **New Request** → **WebSocket** ni tanlang
2. **URL** ga WebSocket URL ni kiriting
3. **Connect** tugmasini bosing
4. **Message** tabida JSON formatda yuboring

**Misol (Postman Message tab):**
```json
{
    "type": "chat_message",
    "message": "Test rasm",
    "file_base64": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
    "file_name": "test.jpg",
    "file_type": "image"
}
```

### 6. Response Format

WebSocket orqali quyidagi formatda javob keladi:

```json
{
    "type": "chat_message",
    "message": "Test rasm",
    "sender": 2,
    "sender_id": 2,
    "sender_name": "Sobirjon Bobojonov",
    "is_from_support": false,
    "created_at": "2025-11-22T14:00:00.000000+00:00",
    "message_id": 52,
    "attachment": "/media/chat/attachments/image/20251122_140000_abc123.jpg",
    "attachment_url": "/media/chat/attachments/image/20251122_140000_abc123.jpg",
    "file_type": "image",
    "file_name": "test.jpg"
}
```

### 7. Fieldlar

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | string | Yes | Har doim `"chat_message"` |
| `message` | string | No | Text xabar (file yuborilganda bo'sh bo'lishi mumkin) |
| `file_base64` | string | No | Base64 encoded file (file yuborilganda required) |
| `file_name` | string | No | Original file nomi (file yuborilganda recommended) |
| `file_type` | string | No | File turi: `"image"`, `"audio"`, yoki `"file"` (file yuborilganda recommended) |

### 8. Eslatmalar

- `file_base64` bo'lsa, `file_name` va `file_type` ham yuborish tavsiya etiladi
- Agar `file_type` yuborilmasa, `file_name` dan extension olinadi
- Agar `file_name` ham yuborilmasa, default extension qo'llaniladi (image uchun .jpg, audio uchun .mp3)
- Base64 string `data:image/jpeg;base64,` prefix bilan ham, prefix siz ham qabul qilinadi

