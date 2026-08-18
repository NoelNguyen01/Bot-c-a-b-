# -*- coding: utf-8 -*-
import discord
from discord.ext import commands
from discord import app_commands
import edge_tts
import asyncio
import os
import uuid
import logging

logger = logging.getLogger("VoiceTTS")

def get_ffmpeg_binary():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


class VoiceTTS(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.ffmpeg_bin = get_ffmpeg_binary()

    def get_user_voice_channel(self, interaction: discord.Interaction):
        # 1. Kiểm tra interaction.user.voice
        if hasattr(interaction.user, "voice") and interaction.user.voice and interaction.user.voice.channel:
            return interaction.user.voice.channel
        
        # 2. Nếu đang gõ trong Text Chat của phòng Voice
        if isinstance(interaction.channel, discord.VoiceChannel):
            return interaction.channel

        # 3. Quét toàn bộ phòng voice trong server tìm member
        if interaction.guild:
            for vc in interaction.guild.voice_channels:
                for member in vc.members:
                    if member.id == interaction.user.id:
                        return vc
        return None

    @app_commands.command(name="join", description="Gọi chị Google vào phòng thoại")
    async def join(self, interaction: discord.Interaction):
        await interaction.response.defer()
        channel = self.get_user_voice_channel(interaction)
        if not channel:
            await interaction.followup.send("Mày phải vào một phòng thoại trước chứ!", ephemeral=True)
            return

        try:
            vc = interaction.guild.voice_client
            if vc and vc.is_connected():
                if vc.channel.id != channel.id:
                    await vc.move_to(channel)
                await interaction.followup.send(f"🔊 Chị Google đã chuyển sang phòng **{channel.name}**, gõ lệnh `/noi` để chị đọc hộ nhé!")
            else:
                if vc:
                    try:
                        await vc.disconnect(force=True)
                    except Exception:
                        pass
                await channel.connect(self_deaf=True, timeout=30.0)
                await interaction.followup.send(f"🔊 Chị Google đã vào phòng **{channel.name}**, đứa nào câm mic thì gõ `/noi` chị đọc hộ!")
        except Exception as e:
            logger.error(f"Lỗi join voice: {e}", exc_info=True)
            await interaction.followup.send(f"❌ Không thể vào phòng thoại: {e}")

    @app_commands.command(name="leave", description="Đuổi chị Google đi")
    async def leave(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if vc is None:
            await interaction.response.send_message("Chị có trong phòng thoại đâu mà đuổi?", ephemeral=True)
            return

        try:
            await vc.disconnect(force=True)
            await interaction.response.send_message("Chị đi đây, lũ hề ở lại vui vẻ. 👋")
        except Exception as e:
            await interaction.response.send_message(f"Lỗi khi rời phòng: {e}", ephemeral=True)

    @app_commands.command(name="noi", description="Nhờ chị Google đọc nội dung")
    async def noi(self, interaction: discord.Interaction, noi_dung: str):
        await interaction.response.defer()
        channel = self.get_user_voice_channel(interaction)
        vc = interaction.guild.voice_client

        # Nếu bot chưa vào voice thì tự động kết nối vào phòng của người dùng
        if not vc or not vc.is_connected():
            if not channel:
                await interaction.followup.send("Mày phải vào một phòng thoại trước thì chị mới biết vào đâu để đọc chứ!", ephemeral=True)
                return
            try:
                if vc:
                    try:
                        await vc.disconnect(force=True)
                    except Exception:
                        pass
                vc = await channel.connect(self_deaf=True, timeout=30.0)
            except Exception as e:
                logger.error(f"Lỗi tự động kết nối voice: {e}", exc_info=True)
                await interaction.followup.send(f"❌ Không thể kết nối vào phòng thoại: {e}")
                return

        if vc.is_playing():
            await interaction.followup.send("Từ từ con lợn ơi, chị đang nói dở!", ephemeral=True)
            return

        file_name = f"/tmp/tts_{uuid.uuid4().hex}.mp3"
        try:
            communicate = edge_tts.Communicate(noi_dung, "vi-VN-HoaiMyNeural")
            await communicate.save(file_name)

            def after_playing(error):
                if error:
                    logger.error(f"Lỗi phát âm thanh: {error}")
                if os.path.exists(file_name):
                    try:
                        os.remove(file_name)
                    except Exception:
                        pass

            source = discord.FFmpegPCMAudio(file_name, executable=self.ffmpeg_bin)
            vc.play(source, after=after_playing)
            await interaction.followup.send(f"🗣️ **Chị Google đã đọc:** {noi_dung}")
        except Exception as e:
            logger.error(f"Lỗi TTS: {e}", exc_info=True)
            if os.path.exists(file_name):
                try:
                    os.remove(file_name)
                except Exception:
                    pass
            await interaction.followup.send(f"❌ Lỗi khi đọc âm thanh: {e}")


async def setup(bot):
    await bot.add_cog(VoiceTTS(bot))
