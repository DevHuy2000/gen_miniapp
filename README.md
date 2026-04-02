# 🇻🇳 FF VN Generator — Telegram Mini App

> Free Fire VN Account Generator chạy trực tiếp trên Telegram

---

## 📁 Cấu trúc project

```
ff-miniapp/
├── vercel.json          ← Cấu hình Vercel routing
├── requirements.txt     ← Python dependencies
├── public/
│   └── index.html       ← Telegram Mini App UI
└── api/
    ├── _core.py         ← Logic tạo acc (từ gen_vn.py)
    ├── generate.py      ← POST /api/generate
    └── status.py        ← GET  /api/status
```

---

## 🚀 Deploy lên Vercel (từng bước)

### Bước 1 — Cài Vercel CLI
```bash
npm install -g vercel
```

### Bước 2 — Login Vercel
```bash
vercel login
```

### Bước 3 — Deploy
```bash
cd ff-miniapp
vercel --prod
```

> Vercel sẽ hỏi vài câu, chọn mặc định hết. Sau khi xong sẽ có URL dạng:
> `https://ff-miniapp-xxx.vercel.app`

### Bước 4 — Test API
Mở browser vào:
```
https://your-url.vercel.app/api/status
```
Phải thấy:
```json
{"status": "ok", "server": "VN", "version": "1.0"}
```

---

## 🤖 Gắn vào Telegram Bot

### 1. Tạo bot (nếu chưa có)
Chat với [@BotFather](https://t.me/BotFather):
```
/newbot
```
Lấy `BOT_TOKEN`

### 2. Gửi lệnh qua API để tạo button Mini App
Dùng Python hoặc Postman:
```python
import requests

BOT_TOKEN = "YOUR_BOT_TOKEN"
CHAT_ID   = "YOUR_CHAT_ID"   # ID của bạn
APP_URL   = "https://your-url.vercel.app"

requests.post(
    f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
    json={
        "chat_id": CHAT_ID,
        "text": "🇻🇳 FF VN Generator",
        "reply_markup": {
            "inline_keyboard": [[{
                "text": "🚀 Mở Generator",
                "web_app": {"url": APP_URL}
            }]]
        }
    }
)
```

### 3. Hoặc dùng BotFather để gắn Menu Button
```
/setmenubutton
→ Chọn bot của bạn
→ Nhập URL: https://your-url.vercel.app
→ Nhập tên nút: 🚀 VN Generator
```

---

## ⚙️ Tuỳ chỉnh

Mở file `api/_core.py`, sửa các biến ở đầu file:
```python
ACCOUNT_NAME  = "Senzu"      # Tiền tố tên acc
PASSWORD_PRE  = "Senzu_999"  # Tiền tố password
RARITY_THRESH = 3            # Ngưỡng điểm để coi là hiếm
```

---

## ⚠️ Lưu ý quan trọng

- Vercel Serverless Function có **timeout 10s** (free tier) / **60s** (Pro)
- Mỗi lần gọi `/api/generate` tạo **1 acc** — Mini App sẽ gọi nhiều lần song song
- **Không lưu acc trên server** — tất cả lưu trong bộ nhớ trình duyệt của session
- Nếu cần lưu vĩnh viễn, thêm tích hợp database (Supabase/PlanetScale free)

---

## 🛠 Chạy local để test

```bash
pip install -r requirements.txt
vercel dev
```
Rồi mở: `http://localhost:3000`

---

## 📞 Luồng hoạt động

```
User nhấn "Bắt đầu"
    ↓
Mini App gọi N lần song song:
    POST /api/generate → _core.py → Garena API
    ↓
Mỗi acc thành công → hiển thị ngay lên UI
    ↓
Nhấn vào card → Copy thông tin
```
