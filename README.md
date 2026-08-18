# 🤡 Discord Bot Siêu Bựa - Chúa Tể Cà Khịa

Bot Discord "phá" dành cho nhóm bạn cùng lớp, viết bằng Python với `discord.py` 2.x, hỗ trợ Slash Commands (`/`).

## ✨ Tính năng

| Lệnh | Mô tả |
|-------|-------|
| `/doino @user <tiền> <lý_do>` | 💸 Máy đòi nợ mặt dày, có nút bấm tương tác |
| `/so_no` | 🏆 Bảng phong thần nợ dai mặt dày |
| `/checklop @user` | 🛞 Quét độ simp / lốp dự phòng (0-100%) |
| `/joker @user <lý_do>` | 🃏 Thả Joker, phong danh thằng hề |
| `/nemda` | 🥷 Ném đá giấu tay / Confession ẩn danh |
| `/spamtag @user <nội_dung> <số_lần>` | 📢 Réo tên vong hồn (max 10 lần, cooldown 45s) |
| `/join` | 🔊 Gọi chị Google vào phòng voice |
| `/leave` | 👋 Đuổi chị Google ra khỏi voice |
| `/noi <nội_dung>` | 🗣️ Chị Google đọc hộ trong voice |

**Tự động:**
- Chào/tiễn bựa khi có người vào/rời **Server**
- Thông báo cà khịa vào text chat của **Voice Room** khi có người vào/ra phòng

---

## 🚀 Hướng dẫn cài đặt & chạy bot

### Bước 1: Tạo Bot trên Discord Developer Portal

1. Truy cập [https://discord.com/developers/applications](https://discord.com/developers/applications)
2. Bấm **New Application** → Đặt tên (ví dụ: `Chúa Tể Cà Khịa`) → **Create**
3. Vào tab **Bot**:
   - Bấm **Reset Token** → Copy token → Lưu lại (chỉ hiện 1 lần!)
   - Bật **MESSAGE CONTENT INTENT** ✅
   - Bật **SERVER MEMBERS INTENT** ✅
   - Bật **PRESENCE INTENT** ✅
4. Vào tab **OAuth2** → **URL Generator**:
   - Scope: chọn `bot` và `applications.commands`
   - Bot Permissions: chọn `Administrator` (cho nhanh)
   - Copy link phía dưới → Dán vào trình duyệt → Mời bot vào server của bạn

### Bước 2: Cài đặt môi trường

```bash
# Cài Python 3.10+ (nếu chưa có)
# Cài ffmpeg (cần cho Voice TTS)
sudo apt install ffmpeg    # Linux
# hoặc: brew install ffmpeg   # macOS

# Clone repo và vào thư mục
git clone <url_repo_của_bạn>
cd class_troll_bot

# Cài thư viện
pip install -r requirements.txt
```

### Bước 3: Cấu hình Token

```bash
# Copy file mẫu
cp .env.example .env

# Mở file .env và dán token vào
nano .env
```

Nội dung file `.env`:
```
DISCORD_TOKEN=MTIxNjU2NzM0MjU4....(token_của_bạn)
```

### Bước 4: Chạy bot

```bash
python3 main.py
```

Khi thấy dòng log:
```
BOT ĐÃ SẴN SÀNG QUẬY PHÁ!
```
Là bot đã online và sẵn sàng tàn phá server! 🎉

---

## 📁 Cấu trúc dự án

```
class_troll_bot/
├── .env                  # Token bí mật (KHÔNG push lên git)
├── .env.example          # File mẫu cấu hình
├── .gitignore            # Bỏ qua .env, cache, data
├── requirements.txt      # Thư viện cần cài
├── main.py               # File chạy bot chính
├── data/
│   └── debts.json        # Dữ liệu sổ nợ
└── cogs/
    ├── troll.py           # Đòi nợ, Check lốp, Joker, Ném đá, Spam tag
    ├── voice_tts.py       # Chị Google đọc hộ (Voice TTS)
    └── welcome.py         # Chào/tiễn bựa Voice & Server
```

---

## ⚠️ Lưu ý

- **KHÔNG BAO GIỜ** chia sẻ file `.env` hoặc Discord Token cho bất kỳ ai!
- Cần cài **ffmpeg** trên máy để tính năng Voice TTS hoạt động.
- Slash commands có thể mất 1-2 phút để đồng bộ lần đầu tiên.
- Lệnh `/spamtag` có cooldown 45 giây để tránh bị Discord ban.
