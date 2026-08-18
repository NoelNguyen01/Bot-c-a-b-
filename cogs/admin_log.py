# -*- coding: utf-8 -*-
import discord
from discord.ext import commands
from discord import app_commands
import json
import os
from datetime import datetime

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

def save_config(data):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


async def send_log_to_admin(guild: discord.Guild, title: str, description: str, color: discord.Color = discord.Color.blue(), fields: list = None):
    """Hàm gửi log vào kênh Admin Log bí mật"""
    if not guild:
        return

    config = load_config()
    guild_id = str(guild.id)
    channel_id = config.get(guild_id, {}).get("admin_log_channel_id")

    channel = None
    if channel_id:
        try:
            channel = guild.get_channel(int(channel_id))
        except Exception:
            pass

    # Tự động tìm kênh có tên admin-log, bot-log, log nếu chưa set
    if not channel:
        for c in guild.channels:
            if any(name in c.name.lower() for name in ["admin-log", "bot-log", "log-admin", "nhat-ky", "logs"]):
                if hasattr(c, "send"):
                    channel = c
                    break

    if channel and hasattr(channel, "send"):
        embed = discord.Embed(
            title=title,
            description=description,
            color=color,
            timestamp=datetime.now()
        )
        if fields:
            for name, val, inline in fields:
                embed.add_field(name=name, value=val, inline=inline)
        embed.set_footer(text="🔒 Nhật Ký Mật Admin")
        try:
            await channel.send(embed=embed)
        except Exception:
            pass


class AdminLogCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="set_admin_log", description="Cài đặt kênh nhận toàn bộ Nhật Ký Hoạt Động bí mật cho Admin (Admin)")
    @app_commands.default_permissions(administrator=True)
    async def set_admin_log(self, interaction: discord.Interaction, channel: discord.abc.GuildChannel):
        user_perms = interaction.user.guild_permissions
        if not (user_perms.administrator or user_perms.manage_guild or user_perms.manage_channels):
            await interaction.response.send_message("❌ Mày phải có quyền Quản trị viên (Admin) mới được dùng lệnh này!", ephemeral=True)
            return

        config = load_config()
        guild_id = str(interaction.guild_id)
        if guild_id not in config:
            config[guild_id] = {}
        config[guild_id]["admin_log_channel_id"] = channel.id
        save_config(config)

        await interaction.response.send_message(
            f"✅ Đã thiết lập Kênh Nhật Ký Admin bí mật tại {channel.mention}!\n🔒 *Toàn bộ hoạt động (ai gửi nặc danh, ai vào/ra, đòi nợ, spam tag...) sẽ được ghi nhật ký vào đây.*",
            ephemeral=True
        )

        # Gửi tin nhắn test vào kênh log
        await send_log_to_admin(
            interaction.guild,
            title="🛡️ KÍCH HOẠT NHẬT KÝ ADMIN THÀNH CÔNG",
            description=f"Admin {interaction.user.mention} đã liên kết kênh này làm **Kênh Nhật Ký Giám Sát Hoạt Động Của Server**.",
            color=discord.Color.green(),
            fields=[
                ("Người cài đặt", f"{interaction.user.name} ({interaction.user.id})", True),
                ("Trạng thái", "🟢 Đang ghi nhật ký 24/7", True)
            ]
        )


async def setup(bot):
    await bot.add_cog(AdminLogCog(bot))
