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
        self.model_name = None
        self.chat_sessions = {}
        self.init_gemini()

    def init_gemini(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            logger.warning("Chưa cấu hình GEMINI_API_KEY!")
            return

        try:
            genai.configure(api_key=self.api_key)
            
            # Tự động quét và chọn Model phù hợp nhất của tài khoản
            candidate_models = ["gemini-1.5-flash", "gemini-1.5-flash-latest", "gemini-2.0-flash", "gemini-1.5-pro", "gemini-pro"]
            selected_model = None
            
            try:
                available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                for cand in candidate_models:
                    for avail in available_models:
                        if cand in avail:
                            selected_model = avail
                            break
                    if selected_model:
                        break
                if not selected_model and available_models:
                    selected_model = available_models[0]
            except Exception as e:
                logger.warning(f"Không thể list models: {e}, dùng mặc định gemini-1.5-flash")
                selected_model = "gemini-1.5-flash"

            self.model_name = selected_model or "gemini-1.5-flash"
            try:
                self.model = genai.GenerativeModel(
                    model_name=self.model_name,
                    system_instruction=SYSTEM_INSTRUCTION
                )
            except Exception:
                # Fallback nếu model cũ không nhận system_instruction
                self.model = genai.GenerativeModel(model_name=self.model_name)

            logger.info(f"🤖 Đã kích hoạt Gemini AI thành công với Model: {self.model_name}")
        except Exception as e:
            logger.error(f"Lỗi khởi tạo Gemini AI: {e}", exc_info=True)

    def get_chat_session(self, channel_id: int):
        if self.model is None:
            self.init_gemini()
        if self.model is None:
            return None

        if channel_id not in self.chat_sessions:
            self.chat_sessions[channel_id] = self.model.start_chat(history=[])
        return self.chat_sessions[channel_id]

    async def generate_ai_response(self, prompt: str, user_name: str, channel_id: int) -> str:
        if self.model is None:
            self.init_gemini()
        if self.model is None:
            return "❌ Chưa cấu hình `GEMINI_API_KEY`! Vui lòng thêm API Key trên Render nhé."

        formatted_prompt = f"[{user_name}]: {prompt}"
        try:
            chat = self.get_chat_session(channel_id)
            response = await asyncio.to_thread(chat.send_message, formatted_prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Lỗi gọi Gemini API: {e}")
            if channel_id in self.chat_sessions:
                del self.chat_sessions[channel_id]
            err_str = str(e)
            if "404" in err_str or "API key not valid" in err_str:
                return (
                    "⚠️ **Mã API Key của bạn chưa đúng định dạng của Google AI Studio!**\n"
                    "👉 Mã API Key chuẩn của Google thường bắt đầu bằng chữ `AIzaSy...`\n"
                    "👉 Bạn hãy vào: https://aistudio.google.com/app/apikey bấm **Create API key** rồi dán lại vào Render nhé!"
                )
            return f"😅 Não tao vừa bị lag một tí: `{err_str}`. Mày hỏi lại câu khác xem nào!"

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
