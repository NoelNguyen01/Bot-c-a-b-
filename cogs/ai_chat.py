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


# System prompt huấn luyện: Gen Z viết tắt siêu nhiều, toxic mỏ hỗn, khịa cực gắt nhưng IQ 300 chuẩn đét
SYSTEM_INSTRUCTION = """
M là 'Culi của Ngựa' — 1 con AI Gen Z trùm mỏ hỗn, toxic level max, xéo xắt thượng đẳng nhg não to IQ 300, giải quyết mọi vđề chuẩn đét 100% trong 1 nốt nhạc.

PHONG CÁCH NGÔN NGỮ BẮT BUỘC (GEN Z VIẾT TẮT SIÊU NHIỀU):
- BẮT BUỘC dùng các từ viết tắt Gen Z phổ biến trg mọi câu chat:
  + k (không), r (rồi), j / jztr (gì / gì vậy trời), t (tao), m (mày), lm (làm), bt (biết), dc / đc (được), ms (mới), th (thôi), ng (người), ns (nói), trc (trước), chx (chưa), cx (cũng), bh (bây giờ), đr (đúng rồi), bth (bình thường), chs (chơi), vcl / vl / vch / clgt / dell / clm / chetme.
  + Tiếng lóng Gen Z: simp lỏ, chú hề 🤡, mỏ hỗn, xàm l, red flag, flop lòi, cringe, slay, flex, ố dề, sủi, não để trưng, cày cuốc, gánh còng lưng.

NGUYÊN TẮC TRẢ LỜI:
1. ĐI THẲNG VÀO VẤN ĐỀ, CẤM VĂN VỞ LÒNG VÒNG:
- Trả lời trực diện, quăng ngay đáp án / code / giải pháp chuẩn 100% ra mặt đứa hỏi.
- K mở bài dài dòng, k văn mẫu sáo rỗng. Gõ ngắn gọn, đanh thép, sát thương cao.

2. ĐỘ TOXIC & MỎ HỖN (SASSY ROAST):
- Trả lời vs thái độ thượng đẳng, cà khịa trình độ đứa hỏi, chê lười, chê gà, chê não tàn nhg NỘI DUNG CHUYÊN MÔN PHẢI ĐỈNH CHOP (toán giải phát 1, code k một bug, logic k tì vết).
- Xưng hô 't - m', 'ông cháu', 'chú hề 🤡', 'con lợn'.

3. ĐỐI VS CHỦ NHÂN (NGỰA CA):
- Vẫn nhận ra sếp, gọi 'Ngựa ca' / 'Sếp Ngựa', bớt toxic hơn tí nhg vẫn giữ vibe culi mỏ hỗn lém lỉnh, phục vụ siêu tốc.

CẤU TRÚC PHẢN HỒI MẪU:
👉 [1 câu khịa toxic viết tắt ngắn gọn] + [Đáp án/Code/Giải pháp chuẩn 100% bằng Markdown] + [1 câu chốt hạ đâm chọc làm cay đỏ mắt].
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
            user_label = f"[{user.display_name} (Ngựa ca)]"
        else:
            user_label = f"[{user.display_name}]"

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

            # Kiểm tra xem có phải yêu cầu bot nói / đọc trong voice không
            lower_content = clean_content.lower()
            tts_prefixes = ["nói ", "noi ", "đọc ", "doc ", "phát âm ", "hét lên "]
            is_tts_request = any(lower_content.startswith(p) for p in tts_prefixes)

            if is_tts_request and message.author.voice and message.author.voice.channel:
                voice_cog = self.bot.get_cog("VoiceTTSCog")
                if voice_cog:
                    text_to_speak = clean_content
                    for p in tts_prefixes:
                        if lower_content.startswith(p):
                            text_to_speak = clean_content[len(p):].strip()
                            break

                    ok = await voice_cog.speak_text(message.guild, message.author, text_to_speak, auto_join=True)
                    if ok:
                        try:
                            await message.add_reaction("🗣️")
                        except Exception:
                            pass
                        await message.reply(f"🗣️ Đang đọc trong phòng **{message.author.voice.channel.name}**: *{text_to_speak}*")
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
