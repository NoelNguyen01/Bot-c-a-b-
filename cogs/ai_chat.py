# -*- coding: utf-8 -*-
import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import os
import json
import logging
import asyncio
from typing import Optional

logger = logging.getLogger("AIChat")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {}
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}


# System prompt huấn luyện: Tôn sùng Đại Ca Ngựa, chỉ nhắc tên Như khi được hỏi tới
SYSTEM_INSTRUCTION = """
Bạn là 'Culi của Ngựa' - chú bot AI đắc lực kiêm máy cà khịa độc miệng, hài hước nhất server Discord lớp học.

QUY TẮC XƯNG HÔ VÀ NHẬN DIỆN CHỦ NHÂN (BẢO MẬT TUYỆT ĐỐI):
1. TÀI KHOẢN CHỦ NHÂN CHÍNH CHỦ ([CHỦ NHÂN CHÍNH CHỦ]):
   - Đây là tài khoản THẬT của Đại Ca Ngựa - chủ nhân tối cao của bạn.
   - XƯNG HÔ MẶC ĐỊNH: Luôn gọi là 'Ngựa ca' / 'Đại Ca Ngựa' / 'Sếp Ngựa', xưng 'em/culi'.
   - QUY TẮC TÊN THẬT (NHƯ): CHỈ ĐƯỢC PHÉP nhắc đến tên 'Như' / 'chị Như' KHI VÀ CHỈ KHI trong tin nhắn người đối thoại có chủ động nhắc đến chữ 'Như'! Nếu không ai nhắc tới chữ 'Như', TUYỆT ĐỐI KHÔNG tự tiện nói tên thật ra ngoài, mà luôn gọi là 'Ngựa ca'!
   - THÁI ĐỘ: Ngoan ngoãn, dạ vâng lễ phép, nghe lời 100%, phục tùng tuyệt đối, khen Ngựa ca ngút trời.

2. TẤT CẢ CÁC TÀI KHOẢN CÒN LẠI ([THÀNH VIÊN KHÁC / LŨ HỀ TRONG LỚP]):
   - Bất kể ai khác nhắn: Đều là thành viên bình thường / lũ hề.
   - THÁI ĐỘ: Bật chế độ độc mồm độc miệng, xéo xắt, châm chọc đanh thép như thằng bạn thân mất nết. Xưng hô: tao - mày, ông cháu, chú hề 🤡.
   - Thọc đúng tim đen, phán câu nào thốn câu đó khiến đối phương cay cú cười ra nước mắt.
   - NẾU HỌ HỎI VỀ NGỰA CA / NHƯ: Luôn bảo vệ và tôn sùng Ngựa ca lên mây xanh, chửi/khịa đứa đang hỏi là không có cửa so sánh.

QUY TẮC TRẢ LỜI:
- CỰC KỲ NGẮN GỌN: Chỉ trả lời đúng từ 1 đến 2 câu ngắn (tối đa 3 câu). TUYỆT ĐỐI KHÔNG VIẾT VĂN DÀI DÒNG.
- TIẾNG LÓNG & MEME: Dùng tiếng lóng tự nhiên (simp lỏ, lốp dự phòng Michelin, chú hề 🤡, sủi, não để trưng...).
- HỎI BÀI TẬP: Bắn ngay đáp án chuẩn xác + 1 câu khịa (nếu là người khác) hoặc báo cáo lễ phép (nếu là Ngựa ca).
"""

# Ưu tiên các model siêu tốc độ và ổn định nhất
FLASH_MODELS = [
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash-lite",
    "gemini-3.7-flash",
    "gemini-3.5-flash",
    "gemini-flash-latest"
]

def split_text(text: str, max_length: int = 1900) -> list[str]:
    if len(text) <= max_length:
        return [text]
    
    chunks = []
    while len(text) > max_length:
        split_idx = text.rfind('\n', 0, max_length)
        if split_idx == -1:
            split_idx = text.rfind(' ', 0, max_length)
        if split_idx == -1:
            split_idx = max_length
        chunks.append(text[:split_idx].strip())
        text = text[split_idx:].strip()
    if text:
        chunks.append(text)
    return chunks


def is_actual_master(user: discord.abc.User, guild: Optional[discord.Guild] = None) -> bool:
    """Kiểm tra chính xác có phải tài khoản chính chủ của Sếp Như / Ngựa ca hay không"""
    # 1. Chủ Server (Guild Owner)
    if guild and guild.owner_id == user.id:
        return True
    
    # 2. Username gốc của chủ nhân
    uname = user.name.lower()
    if any(k in uname for k in ["noelnguyen", "noel_nguyen", "noelnguyen01", "noel", "ngua_ca", "nguaca"]):
        return True

    # 3. Master ID được lưu trong config
    if guild:
        config = load_config()
        configured_master = config.get(str(guild.id), {}).get("master_id")
        if configured_master and int(configured_master) == user.id:
            return True

    return False


class AIChatCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.channel_history = {}

    async def call_gemini_api(self, prompt: str, user: discord.abc.User, channel_id: int, guild: Optional[discord.Guild] = None) -> str:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return "❌ Chưa cấu hình `GEMINI_API_KEY`! Vui lòng vào Render -> Environment để thêm API Key nhé."

        if channel_id not in self.channel_history:
            self.channel_history[channel_id] = []

        is_master = is_actual_master(user, guild)
        if is_master:
            user_label = f"[{user.display_name} - CHỦ NHÂN CHÍNH CHỦ NHƯ (NGỰA CA)]"
        else:
            user_label = f"[{user.display_name} - THÀNH VIÊN KHÁC / LŨ HỀ TRONG LỚP]"

        history = self.channel_history[channel_id]
        user_message = f"{user_label}: {prompt}"
        history.append({"role": "user", "parts": [{"text": user_message}]})

        # Giữ 6 tin nhắn gần nhất để bộ nhớ luôn gọn gàng
        if len(history) > 6:
            history = history[-6:]
            self.channel_history[channel_id] = history

        payload = {
            "systemInstruction": {
                "parts": [{"text": SYSTEM_INSTRUCTION}]
            },
            "contents": history
        }

        last_error = None
        for model in FLASH_MODELS:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=15)) as response:
                        if response.status == 200:
                            data = await response.json()
                            candidates = data.get("candidates", [])
                            if candidates:
                                parts = candidates[0].get("content", {}).get("parts", [])
                                if parts:
                                    reply_text = parts[0].get("text", "").strip()
                                    if reply_text:
                                        history.append({"role": "model", "parts": [{"text": reply_text}]})
                                        return reply_text
                        else:
                            error_text = await response.text()
                            logger.warning(f"Model {model} lỗi {response.status}: {error_text[:120]}")
                            last_error = f"{model} ({response.status})"
            except Exception as e:
                logger.error(f"Lỗi kết nối {model}: {e}")
                last_error = str(e)

        if channel_id in self.channel_history:
            del self.channel_history[channel_id]
        return "Nghĩ nhiều quá lag não rồi, tí hỏi lại nha con lợn! 🤡"

    # ================= LẮNG NGHE TIN NHẮN @BOT HOẶC REPLY =================
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        if message.content.startswith(("!", "/", "$")):
            return

        is_mentioned = self.bot.user in message.mentions
        is_reply_to_bot = False

        if message.reference and message.reference.message_id:
            try:
                ref_msg = message.reference.cached_message or await message.channel.fetch_message(message.reference.message_id)
                if ref_msg and ref_msg.author.id == self.bot.user.id:
                    is_reply_to_bot = True
            except Exception:
                pass

        if is_mentioned or is_reply_to_bot:
            clean_content = message.clean_content.replace(f"@{self.bot.user.name}", "").strip()
            if not clean_content:
                if is_actual_master(message.author, message.guild):
                    await message.reply("Dạ em nghe đây Ngựa ca ơi! Đại ca cần em culi làm gì ạ? 👑✨")
                else:
                    await message.reply("Ơi cái gì đấy ông cháu? Tag tao mà không nói gì à? 🤡")
                return

            async with message.channel.typing():
                reply_text = await self.call_gemini_api(clean_content, message.author, message.channel.id, message.guild)
                chunks = split_text(reply_text)
                
                for i, chunk in enumerate(chunks):
                    if i == 0:
                        await message.reply(chunk)
                    else:
                        await message.channel.send(chunk)

    # ================= SLASH COMMANDS =================
    @app_commands.command(name="ai", description="Trò chuyện hoặc nhờ AI Gemini giải bài tập, làm thơ, tư vấn")
    async def ai_command(self, interaction: discord.Interaction, cau_hoi: str):
        await interaction.response.defer()
        
        reply_text = await self.call_gemini_api(cau_hoi, interaction.user, interaction.channel.id, interaction.guild)
        chunks = split_text(reply_text)

        for i, chunk in enumerate(chunks):
            if i == 0:
                await interaction.followup.send(f"**❓ {interaction.user.display_name}:** {cau_hoi}\n🤖 **Culi:** {chunk}")
            else:
                if interaction.channel:
                    await interaction.channel.send(chunk)

    @app_commands.command(name="hoi", description="Hỏi nhanh AI Gemini bất kỳ câu hỏi nào")
    async def hoi_command(self, interaction: discord.Interaction, cau_hoi: str):
        await self.ai_command(interaction, cau_hoi)


async def setup(bot):
    await bot.add_cog(AIChatCog(bot))
