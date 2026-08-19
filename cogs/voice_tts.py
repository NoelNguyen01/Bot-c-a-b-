# -*- coding: utf-8 -*-
import discord
from discord.ext import commands
from discord import app_commands
import edge_tts
import asyncio
import os
import uuid
import re
import logging
from typing import Optional

logger = logging.getLogger("VoiceTTS")

def get_ffmpeg_binary():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


# TỪ ĐIỂN DỊCH VIẾT TẮT / TEENCODE TIẾNG VIỆT TOÀN DIỆN
VIETNAMESE_ABBREVIATIONS = {
    # Đại từ & xưng hô
    r'\bt\b': 'tao',
    r'\bm\b': 'mày',
    r'\bng\b': 'người',
    r'\bngừi\b': 'người',
    r'\bae\b': 'anh em',
    r'\bmn\b': 'mọi người',
    r'\bmk\b': 'mình',
    r'\bmik\b': 'mình',
    r'\bthg\b': 'thằng',
    r'\btk\b': 'thằng',
    r'\bthk\b': 'thằng',
    r'\bad\b': 'admin',
    r'\bgv\b': 'giáo viên',
    r'\bhs\b': 'học sinh',
    r'\bcr\b': 'crush',

    # Các từ viết tắt phổ biến nhất
    r'\bk\b': 'không',
    r'\bko\b': 'không',
    r'\bkh\b': 'không',
    r'\bkhong\b': 'không',
    r'\bk0\b': 'không',
    r'\bdc\b': 'được',
    r'\bđc\b': 'được',
    r'\bđk\b': 'được',
    r'\br\b': 'rồi',
    r'\broi\b': 'rồi',
    r'\bchx\b': 'chưa',
    r'\bj\b': 'gì',
    r'\bv\b': 'vậy',
    r'\bvaayj\b': 'vậy',
    r'\bs\b': 'sao',
    r'\bcx\b': 'cũng',
    r'\bvs\b': 'với',
    r'\bnx\b': 'nữa',
    r'\bth\b': 'thôi',
    r'\bthui\b': 'thôi',
    r'\blm\b': 'làm',
    r'\bns\b': 'nói',
    r'\bbt\b': 'biết',
    r'\bh\b': 'giờ',
    r'\bbh\b': 'bây giờ',
    r'\btrg\b': 'trong',
    r'\btrog\b': 'trong',
    r'\bnt\b': 'nhắn tin',
    r'\bdr\b': 'đúng rồi',
    r'\bđr\b': 'đúng rồi',
    r'\buk\b': 'ừ',
    r'\buh\b': 'ừ',
    r'\bum\b': 'ừ',
    r'\bkp\b': 'không phải',
    r'\bcb\b': 'chuẩn bị',
    r'\bok\b': 'ô kê',
    r'\boke\b': 'ô kê',
    r'\boki\b': 'ô kê',
    r'\bacc\b': 'tài khoản',
    r'\bpass\b': 'mật khẩu',
    r'\bstt\b': 'số thứ tự',
    r'\bbtvn\b': 'bài tập về nhà',
    r'\bhw\b': 'bài tập về nhà',
    r'\btkb\b': 'thời khóa biểu',

    # Mạng xã hội & công nghệ
    r'\bsv\b': 'máy chủ',
    r'\bvc\b': 'phòng thoại',
    r'\bmic\b': 'míc',
    r'\bcam\b': 'cam-mê-ra',
    r'\bfb\b': 'phây búc',
    r'\big\b': 'in-sta-gram',
    r'\bytb\b': 'diu túp',
    r'\btt\b': 'tóp tóp',
    r'\btiktok\b': 'tóp tóp',
    r'\bdis\b': 'đít cọt',
    r'\bdiscord\b': 'đít cọt',

    # Tiếng lóng & cảm thán vui
    r'\bclgt\b': 'cái lề gì thốn',
    r'\bvl\b': 'vãi lúa',
    r'\bvcl\b': 'vãi cả lúa',
    r'\bvkl\b': 'vãi cả lúa',
    r'\bvch\b': 'vãi chưởng',
    r'\bvcc\b': 'vãi cà chua',
    r'\bdm\b': 'đờ mờ',
    r'\bđm\b': 'đờ mờ',
    r'\bdcm\b': 'đờ cờ mờ',
    r'\bđcm\b': 'đờ cờ mờ',
    r'\bdmm\b': 'đờ mờ mày',
    r'\bđmm\b': 'đờ mờ mày',
    r'\bcl\b': 'cờ lờ',
    r'\bcc\b': 'cục cứt',
    r'\bcmnr\b': 'chuẩn mẹ nó rồi',
    r'\bvcb\b': 'vãi cả bưởi',
}


def clean_text_for_tts(text: str) -> str:
    """Lọc, dịch viết tắt và làm sạch văn bản trước khi đọc"""
    # 1. Bỏ link URL
    text = re.sub(r'https?://\S+|www\.\S+', 'gửi một đường link', text)
    # 2. Bỏ mention
    text = re.sub(r'<@!?\d+>', 'ai đó', text)
    text = re.sub(r'<#\d+>', 'kênh', text)
    text = re.sub(r'<@&\d+>', 'vai trò', text)

    # 3. TỰ ĐỘNG DỊCH TỪ VIẾT TẮT / TEENCODE SANG TIẾNG VIỆT CHUẨN
    for pattern, replacement in VIETNAMESE_ABBREVIATIONS.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    # 4. Giới hạn tối đa 200 ký tự chống spam
    if len(text) > 200:
        text = text[:200] + "... dài quá lười đọc!"
    return text.strip()


class VoiceTTS(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.ffmpeg_bin = get_ffmpeg_binary()
        self.queues = {}
        self.worker_tasks = {}
        self.autotts_enabled = {}

    def get_queue(self, guild_id: int) -> asyncio.Queue:
        if guild_id not in self.queues:
            self.queues[guild_id] = asyncio.Queue()
        return self.queues[guild_id]

    def ensure_worker(self, guild: discord.Guild):
        guild_id = guild.id
        task = self.worker_tasks.get(guild_id)
        if task is None or task.done():
            self.worker_tasks[guild_id] = asyncio.create_task(self.queue_worker(guild))

    async def queue_worker(self, guild: discord.Guild):
        guild_id = guild.id
        queue = self.get_queue(guild_id)

        while True:
            try:
                item = await queue.get()
                text_to_read, original_channel = item

                vc = guild.voice_client
                if not vc or not vc.is_connected():
                    queue.task_done()
                    continue

                file_name = f"/tmp/tts_{uuid.uuid4().hex}.mp3"
                try:
                    communicate = edge_tts.Communicate(text_to_read, "vi-VN-HoaiMyNeural")
                    await communicate.save(file_name)

                    while vc.is_playing() or vc.is_paused():
                        await asyncio.sleep(0.2)

                    source = discord.FFmpegPCMAudio(file_name, executable=self.ffmpeg_bin)
                    vc.play(source)

                    while vc.is_playing():
                        await asyncio.sleep(0.2)

                except Exception as e:
                    logger.error(f"Lỗi khi phát âm thanh TTS: {e}")
                finally:
                    if os.path.exists(file_name):
                        try:
                            os.remove(file_name)
                        except Exception:
                            pass
                    queue.task_done()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Lỗi trong queue_worker: {e}")
                await asyncio.sleep(0.5)

    def get_user_voice_channel(self, user: discord.Member, guild: discord.Guild):
        if hasattr(user, "voice") and user.voice and user.voice.channel:
            return user.voice.channel
        for vc in guild.voice_channels:
            if user in vc.members:
                return vc
        return None

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        guild = message.guild
        vc = guild.voice_client

        if not vc or not vc.is_connected():
            return

        if not self.autotts_enabled.get(guild.id, True):
            return

        content = message.content.strip()
        if not content or content.startswith(("!", "/", "$", ".", "?")):
            return

        is_in_vc_text = (isinstance(message.channel, discord.VoiceChannel) and message.channel.id == vc.channel.id)
        user_in_same_vc = (hasattr(message.author, "voice") and message.author.voice and message.author.voice.channel and message.author.voice.channel.id == vc.channel.id)

        if is_in_vc_text or user_in_same_vc:
            clean_msg = clean_text_for_tts(content)
            if not clean_msg:
                return

            text_to_speak = f"{message.author.display_name} nói: {clean_msg}"
            queue = self.get_queue(guild.id)
            await queue.put((text_to_speak, message.channel))
            self.ensure_worker(guild)

    @app_commands.command(name="join", description="Mời chị Google vào phòng voice & Tự động đọc tin nhắn chat")
    async def join(self, interaction: discord.Interaction):
        await interaction.response.defer()
        channel = self.get_user_voice_channel(interaction.user, interaction.guild)
        if not channel:
            await interaction.followup.send("❌ Bạn phải vào một phòng thoại trước chứ!", ephemeral=True)
            return

        try:
            vc = interaction.guild.voice_client
            if vc and vc.is_connected():
                if vc.channel.id != channel.id:
                    await vc.move_to(channel)
            else:
                if vc:
                    try:
                        await vc.disconnect(force=True)
                    except Exception:
                        pass
                vc = await channel.connect(self_deaf=True, timeout=30.0)

            self.autotts_enabled[interaction.guild_id] = True
            self.ensure_worker(interaction.guild)

            embed = discord.Embed(
                title="🎙️ CHỊ GOOGLE ĐÃ VÀO PHÒNG & KÍCH HOẠT TỰ ĐỘNG ĐỌC! ✨",
                description=(
                    f"🔊 Đã kết nối vào phòng **{channel.name}**.\n\n"
                    "💡 **TÍNH NĂNG TỰ ĐỘNG ĐỌC (AUTO-TTS):**\n"
                    "👉 Anh em câm mic chỉ cần **nhắn tin chữ bình thường** vào kênh chat phòng Voice này, "
                    "chị Google sẽ **tự động phát giọng đọc vào mic** mà không cần gõ lệnh gì cả!\n"
                    "*(Đã hỗ trợ dịch hơn 60 từ viết tắt: k, ko, dc, t, m, v, r, clgt, vl...)*\n\n"
                    "*(Dùng `/leave` để đuổi chị đi, hoặc `/autotts tat` nếu muốn tắt tự đọc)*"
                ),
                color=discord.Color.green()
            )
            embed.set_thumbnail(url="https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/72x72/1f399.png")
            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"Lỗi join voice: {e}", exc_info=True)
            await interaction.followup.send(f"❌ Không thể vào phòng thoại: {e}")

    @app_commands.command(name="leave", description="Cho chị Google rời khỏi phòng thoại")
    async def leave(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if vc is None:
            await interaction.response.send_message("Chị có trong phòng thoại đâu mà đuổi?", ephemeral=True)
            return

        guild_id = interaction.guild_id
        if guild_id in self.worker_tasks:
            self.worker_tasks[guild_id].cancel()
            del self.worker_tasks[guild_id]
        if guild_id in self.queues:
            del self.queues[guild_id]

        try:
            await vc.disconnect(force=True)
            await interaction.response.send_message("👋 Chị đi đây, lũ hề ở lại vui vẻ!")
        except Exception as e:
            await interaction.response.send_message(f"Lỗi khi rời phòng: {e}", ephemeral=True)

    @app_commands.command(name="autotts", description="Bật hoặc Tắt chế độ tự động đọc tin nhắn trong phòng Voice")
    @app_commands.choices(trang_thai=[
        app_commands.Choice(name="🟢 Bật tự động đọc", value="on"),
        app_commands.Choice(name="🔴 Tắt tự động đọc", value="off")
    ])
    async def autotts(self, interaction: discord.Interaction, trang_thai: app_commands.Choice[str]):
        is_on = (trang_thai.value == "on")
        self.autotts_enabled[interaction.guild_id] = is_on
        
        status_text = "🟢 **ĐÃ BẬT** Tự động đọc tin nhắn chat!" if is_on else "🔴 **ĐÃ TẮT** Tự động đọc tin nhắn chat!"
        desc = "Từ giờ bất kỳ tin nhắn nào trong kênh thoại sẽ được chị đọc to vào mic!" if is_on else "Chị sẽ chỉ đọc khi bạn dùng lệnh `/noi`!"
        
        embed = discord.Embed(
            title=status_text,
            description=desc,
            color=discord.Color.green() if is_on else discord.Color.red()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="noi", description="Nhờ chị Google đọc một câu cụ thể")
    async def noi(self, interaction: discord.Interaction, noi_dung: str):
        await interaction.response.defer()
        guild = interaction.guild
        vc = guild.voice_client

        if not vc or not vc.is_connected():
            channel = self.get_user_voice_channel(interaction.user, guild)
            if not channel:
                await interaction.followup.send("❌ Bạn phải vào một phòng thoại trước!", ephemeral=True)
                return
            try:
                vc = await channel.connect(self_deaf=True, timeout=30.0)
            except Exception as e:
                await interaction.followup.send(f"❌ Không thể kết nối voice: {e}")
                return

        clean_msg = clean_text_for_tts(noi_dung)
        text_to_speak = f"{interaction.user.display_name} nói: {clean_msg}"

        queue = self.get_queue(guild.id)
        await queue.put((text_to_speak, interaction.channel))
        self.ensure_worker(guild)

        await interaction.followup.send(f"🗣️ **Đã xếp hàng đọc:** {clean_msg}")

    @commands.command(name="join")
    async def cmd_join(self, ctx):
        channel = self.get_user_voice_channel(ctx.author, ctx.guild)
        if not channel:
            await ctx.send("❌ Bạn phải vào phòng thoại trước!")
            return
        vc = ctx.guild.voice_client
        if vc and vc.is_connected():
            await vc.move_to(channel)
        else:
            await channel.connect(self_deaf=True, timeout=30.0)
        self.autotts_enabled[ctx.guild.id] = True
        self.ensure_worker(ctx.guild)
        await ctx.send(f"🎙️ **Chị Google đã vào {channel.name}!** Tự động đọc tin nhắn chat đã kích hoạt!")

    @commands.command(name="leave")
    async def cmd_leave(self, ctx):
        vc = ctx.guild.voice_client
        if vc:
            await vc.disconnect(force=True)
            await ctx.send("👋 Chị đi đây!")


async def setup(bot):
    await bot.add_cog(VoiceTTS(bot))
