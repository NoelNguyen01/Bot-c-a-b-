# -*- coding: utf-8 -*-
import discord
from discord.ext import commands
from discord import app_commands
import edge_tts
import asyncio
import os
import uuid

class VoiceTTS(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="join", description="Gọi chị Google vào phòng thoại")
    async def join(self, interaction: discord.Interaction):
        if not interaction.user.voice:
            await interaction.response.send_message("Mày phải vào phòng thoại trước chứ!", ephemeral=True)
            return
        
        channel = interaction.user.voice.channel
        try:
            if interaction.guild.voice_client:
                await interaction.guild.voice_client.move_to(channel)
            else:
                await channel.connect()
            await interaction.response.send_message("Chị Google đã vào phòng, đứa nào câm mic thì gõ lệnh /noi chị đọc hộ.")
        except Exception as e:
            await interaction.response.send_message(f"Không thể vào phòng thoại: {e}", ephemeral=True)

    @app_commands.command(name="leave", description="Đuổi chị Google đi")
    async def leave(self, interaction: discord.Interaction):
        if interaction.guild.voice_client is None:
            await interaction.response.send_message("Chị có trong phòng đâu mà đuổi?", ephemeral=True)
            return

        try:
            await interaction.guild.voice_client.disconnect()
            await interaction.response.send_message("Chị đi đây, lũ hề ở lại vui vẻ. 👋")
        except Exception as e:
            await interaction.response.send_message(f"Lỗi khi rời phòng: {e}", ephemeral=True)

    @app_commands.command(name="noi", description="Nhờ chị Google đọc nội dung")
    async def noi(self, interaction: discord.Interaction, noi_dung: str):
        voice_client = interaction.guild.voice_client
        if not voice_client or not voice_client.is_connected():
            await interaction.response.send_message("Mày chưa gọi chị vào phòng, dùng /join trước đi!", ephemeral=True)
            return

        if voice_client.is_playing():
            await interaction.response.send_message("Từ từ, chị đang nói!", ephemeral=True)
            return

        await interaction.response.defer()

        file_name = f"/tmp/tts_{uuid.uuid4().hex}.mp3"
        try:
            communicate = edge_tts.Communicate(noi_dung, "vi-VN-HoaiMyNeural")
            await communicate.save(file_name)

            def after_playing(error):
                if os.path.exists(file_name):
                    try:
                        os.remove(file_name)
                    except Exception:
                        pass

            source = discord.FFmpegPCMAudio(file_name)
            voice_client.play(source, after=after_playing)
            await interaction.followup.send(f"🗣️ **Chị Google đã đọc:** {noi_dung}")
        except Exception as e:
            if os.path.exists(file_name):
                try:
                    os.remove(file_name)
                except Exception:
                    pass
            await interaction.followup.send(f"❌ Lỗi khi đọc âm thanh: {e}")


async def setup(bot):
    await bot.add_cog(VoiceTTS(bot))
