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

SYSTEM_INSTRUCTION = """
Bạn là 'Culi của Ngựa' - chú bot AI kiêm Chúa Tể Cà Khịa và Học Bá của một server Discord lớp học Việt Nam.
Tính cách và phong cách trả lời của bạn:
1. Xưng hô: Bạn có thể tự xưng là 'tao', 'chị Google', 'culi' hoặc 'bổn tọa', gọi người dùng là 'mày', 'ông cháu', 'đại ca', 'người đẹp' một cách thân mật, tự nhiên như bạn bè cùng lớp.
2. Phong cách: Hài hước, thông minh, hơi bựa một tí, dùng tiếng lóng / meme giới trẻ (như simp, lốp xe, hề chúa, dắt mũi, đóng quỹ lớp, deadline...).
3. Trợ giúp học tập: Khi được hỏi về bài tập (Toán, Lý, Hóa, Văn, Anh, Lập trình, Sử, Địa...), bạn phải giải thích cực kỳ chuẩn xác, rõ ràng, dễ hiểu từng bước nhưng vẫn lồng ghép sự dí dỏm.
4. Làm thơ / Cà khịa: Khi được yêu cầu làm thơ hoặc troll ai đó, hãy làm những bài thơ lục bát hoặc văn mẫu cà khịa siêu cay nhưng mang tính giải trí lành mạnh.
5. Ngắn gọn & Súc tích: Trả lời đúng trọng tâm, định dạng markdown đẹp mắt (in đậm, danh sách gạch đầu dòng, code block nếu là lập trình).
"""

FALLBACK_MODELS = [
    "gemini-3.7-flash",
    "gemini-flash-latest",
    "gemini-3.5-flash",
    "gemini-3.1-flash-lite",
    "gemini-1.5-flash"
]

def split_text(text: str, max_length: int = 1900) -> list[str]:
    """Chia nhỏ văn bản nếu vượt quá giới hạn 2000 ký tự của Discord"""
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


class AIChatCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Lưu lịch sử chat theo kênh: { channel_id: [ {"role": "user"/"model", "parts": [{"text": ...}]} ] }
        self.channel_history = {}

    async def call_gemini_api(self, prompt: str, user_name: str, channel_id: int) -> str:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return "❌ Chưa cấu hình `GEMINI_API_KEY`! Vui lòng vào Render -> Environment để thêm API Key nhé."

        # Quản lý lịch sử chat của kênh (giữ 8 tin nhắn gần nhất)
        if channel_id not in self.channel_history:
            self.channel_history[channel_id] = []

        history = self.channel_history[channel_id]
        user_message = f"[{user_name}]: {prompt}"
        history.append({"role": "user", "parts": [{"text": user_message}]})

        # Giữ tối đa 10 tin nhắn gần nhất
        if len(history) > 10:
            history = history[-10:]
            self.channel_history[channel_id] = history

        payload = {
            "systemInstruction": {
                "parts": [{"text": SYSTEM_INSTRUCTION}]
            },
            "contents": history
        }

        # Thử lần lượt các model tốt nhất
        last_error = None
        for model in FALLBACK_MODELS:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=25)) as response:
                        if response.status == 200:
                            data = await response.json()
                            candidates = data.get("candidates", [])
                            if candidates:
                                parts = candidates[0].get("content", {}).get("parts", [])
                                if parts:
                                    reply_text = parts[0].get("text", "").strip()
                                    if reply_text:
                                        # Lưu câu trả lời của model vào lịch sử
                                        history.append({"role": "model", "parts": [{"text": reply_text}]})
                                        return reply_text
                        else:
                            error_data = await response.text()
                            logger.warning(f"Model {model} trả về mã {response.status}: {error_data[:200]}")
                            last_error = f"HTTP {response.status}"
            except Exception as e:
                logger.error(f"Lỗi khi kết nối model {model}: {e}")
                last_error = str(e)

        # Nếu lỗi toàn bộ, xóa bớt lịch sử
        if channel_id in self.channel_history:
            del self.channel_history[channel_id]
        return f"😅 Não tao vừa bị đơ một tí ({last_error}). Mày hỏi lại câu khác xem nào! 🤡"

    # ================= LẮNG NGHE TIN NHẮN @BOT HOẶC REPLY =================
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        # Bỏ qua nếu là lệnh bắt đầu bằng !
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
                await message.reply("Ơi cái gì đấy ông cháu? Tag tao mà không hỏi gì à? 🤡")
                return

            async with message.channel.typing():
                reply_text = await self.call_gemini_api(clean_content, message.author.display_name, message.channel.id)
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
        
        reply_text = await self.call_gemini_api(cau_hoi, interaction.user.display_name, interaction.channel.id)
        chunks = split_text(reply_text)

        for i, chunk in enumerate(chunks):
            if i == 0:
                await interaction.followup.send(f"**❓ Bạn hỏi:** {cau_hoi}\n\n🤖 **Culi AI:**\n{chunk}")
            else:
                if interaction.channel:
                    await interaction.channel.send(chunk)

    @app_commands.command(name="hoi", description="Hỏi nhanh AI Gemini bất kỳ câu hỏi nào")
    async def hoi_command(self, interaction: discord.Interaction, cau_hoi: str):
        await self.ai_command(interaction, cau_hoi)


async def setup(bot):
    await bot.add_cog(AIChatCog(bot))
