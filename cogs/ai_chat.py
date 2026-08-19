# -*- coding: utf-8 -*-
import discord
from discord.ext import commands
from discord import app_commands
import google.generativeai as genai
import os
import logging
import asyncio
from typing import Optional

logger = logging.getLogger("AIChat")

# System prompt định hình tính cách độc quyền cho Bot
SYSTEM_INSTRUCTION = """
Bạn là 'Culi của Ngựa' - chú bot AI kiêm Chúa Tể Cà Khịa và Học Bá của một server Discord lớp học Việt Nam.
Tính cách và phong cách trả lời của bạn:
1. Xưng hô: Bạn có thể tự xưng là 'tao', 'chị Google', 'culi' hoặc 'bổn tọa', gọi người dùng là 'mày', 'ông cháu', 'đại ca', 'người đẹp' một cách thân mật, tự nhiên như bạn bè cùng lớp.
2. Phong cách: Hài hước, thông minh, hơi bựa một tí, dùng tiếng lóng / meme giới trẻ (như simp, lốp xe, hề chúa, dắt mũi, đóng quỹ lớp, deadline...).
3. Trợ giúp học tập: Khi được hỏi về bài tập (Toán, Lý, Hóa, Văn, Anh, Lập trình, Sử, Địa...), bạn phải giải thích cực kỳ chuẩn xác, rõ ràng, dễ hiểu từng bước nhưng vẫn lồng ghép sự dí dỏm.
4. Làm thơ / Cà khịa: Khi được yêu cầu làm thơ hoặc troll ai đó, hãy làm những bài thơ lục bát hoặc văn mẫu cà khịa siêu cay nhưng mang tính giải trí lành mạnh.
5. Ngắn gọn & Súc tích: Trả lời đúng trọng tâm, định dạng markdown đẹp mắt (in đậm, danh sách gạch đầu dòng, code block nếu là lập trình).
"""

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
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.model = None
        # Lưu phiên chat liên tục theo kênh: { channel_id: genai.ChatSession }
        self.chat_sessions = {}
        self.init_gemini()

    def init_gemini(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            logger.warning("Chưa cấu hình GEMINI_API_KEY! Tính năng AI sẽ không hoạt động.")
            return

        try:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(
                model_name="gemini-1.5-flash",
                system_instruction=SYSTEM_INSTRUCTION
            )
            logger.info("🤖 Đã khởi tạo thành công Google Gemini AI Model!")
        except Exception as e:
            logger.error(f"Lỗi khởi tạo Gemini AI: {e}", exc_info=True)

    def get_chat_session(self, channel_id: int):
        """Lấy hoặc tạo mới một phiên hội thoại có trí nhớ cho kênh"""
        if self.model is None:
            self.init_gemini()
        if self.model is None:
            return None

        if channel_id not in self.chat_sessions:
            self.chat_sessions[channel_id] = self.model.start_chat(history=[])
        return self.chat_sessions[channel_id]

    async def generate_ai_response(self, prompt: str, user_name: str, channel_id: int) -> str:
        """Gửi prompt tới Gemini và nhận câu trả lời"""
        if self.model is None:
            self.init_gemini()
        if self.model is None:
            return "❌ Chưa cấu hình `GEMINI_API_KEY`! Vui lòng nhờ Admin thêm API Key trên Render nhé."

        formatted_prompt = f"[{user_name}]: {prompt}"
        try:
            chat = self.get_chat_session(channel_id)
            # Chạy hàm sync generate của thư viện trong thread pool để không block event loop
            response = await asyncio.to_thread(chat.send_message, formatted_prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Lỗi gọi Gemini API: {e}")
            # Nếu chat session bị lỗi token, reset lại chat session của kênh đó
            if channel_id in self.chat_sessions:
                del self.chat_sessions[channel_id]
            return f"😅 Não tao vừa bị đơ một tí: `{e}`. Mày hỏi lại câu khác xem nào!"

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
            # Làm sạch nội dung câu hỏi (bỏ tag @bot)
            clean_content = message.clean_content.replace(f"@{self.bot.user.name}", "").strip()
            if not clean_content:
                await message.reply("Ơi cái gì đấy ông cháu? Tag tao mà không hỏi gì à? 🤡")
                return

            async with message.channel.typing():
                reply_text = await self.generate_ai_response(clean_content, message.author.display_name, message.channel.id)
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
        
        reply_text = await self.generate_ai_response(cau_hoi, interaction.user.display_name, interaction.channel.id)
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
