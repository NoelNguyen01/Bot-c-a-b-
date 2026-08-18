# -*- coding: utf-8 -*-
import discord
from discord.ext import commands
from discord import app_commands
from typing import Union
import random
import json
import os

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


class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.join_messages = [
            "Chào mừng con mồi mới {tag} đã gia nhập chuồng hề. 🤡",
            "Ơ kìa {tag} lạc vào chuồng thú rồi à? Chào mừng nhé! 🎪",
            "Thêm một nạn nhân mới... à nhầm, thêm một thành viên mới {tag}! Chào mừng! 🎉",
            "Hú hú {tag} ơi! Vào chuồng nhớ chào các đại ca nhé! 🐒"
        ]
        self.leave_messages = [
            "Tiễn vong **{name}**, không chịu nổi nhiệt đã bấm nút biến. 💨",
            "**{name}** đã sủi rồi nhé cả nhà, F trong chat. ⚰️",
            "Một con chim đã rời đàn... **{name}** bay đi không một lời từ biệt. 🕊️"
        ]
        self.vc_join_messages = [
            "Chào mừng đại ca {mention} đã mò mặt vào chuồng. 🎙️",
            "{mention} đã xuất hiện! Huyền thoại trở lại! 👑",
            "Ơ kìa {mention} hôm nay cũng rảnh à? 😏",
            "Cả lò chú ý: {mention} đã vào phòng! 🚨"
        ]
        self.vc_leave_messages = [
            "{mention} lại sủi đi ỉa rồi à? 💩",
            "{mention} đã cúp đuôi chạy trốn. 🏃",
            "{mention} biến mất nhanh hơn crush rep tin nhắn mày. 💨"
        ]

    @app_commands.command(name="set_welcome", description="Cài đặt kênh gửi tin nhắn chào mừng/tiễn thành viên")
    async def set_welcome(
        self, 
        interaction: discord.Interaction, 
        channel: Union[discord.TextChannel, discord.NewsChannel, discord.VoiceChannel, discord.Thread]
    ):
        user_perms = interaction.user.guild_permissions
        if not (user_perms.administrator or user_perms.manage_guild or user_perms.manage_channels):
            await interaction.response.send_message("❌ Mày phải có quyền Quản trị viên (Admin) hoặc Quản lý kênh mới được dùng lệnh này nha!", ephemeral=True)
            return

        try:
            config = load_config()
            guild_id = str(interaction.guild_id)
            if guild_id not in config:
                config[guild_id] = {}
            config[guild_id]["welcome_channel_id"] = channel.id
            save_config(config)
            await interaction.response.send_message(f"✅ Đã cài đặt kênh chào mừng thành viên tại {channel.mention}!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Lỗi khi lưu cài đặt: {e}", ephemeral=True)

    @app_commands.command(name="set_autorole", description="Cài đặt vai trò tự động cấp cho thành viên mới khi vào Server")
    async def set_autorole(self, interaction: discord.Interaction, role: discord.Role):
        user_perms = interaction.user.guild_permissions
        if not (user_perms.administrator or user_perms.manage_guild or user_perms.manage_roles):
            await interaction.response.send_message("❌ Mày phải có quyền Quản trị viên (Admin) hoặc Quản lý vai trò mới được dùng lệnh này nha!", ephemeral=True)
            return

        # Kiểm tra xem bot có quyền cấp role này không
        if role >= interaction.guild.me.top_role:
            await interaction.response.send_message(
                f"❌ Vai trò {role.mention} cao hơn hoặc bằng vai trò của Bot!\n👉 **Cách sửa:** Vào *Cài đặt Server -> Vai trò*, kéo vai trò của Bot lên **trên** vai trò {role.name} nhé.",
                ephemeral=True
            )
            return

        try:
            config = load_config()
            guild_id = str(interaction.guild_id)
            if guild_id not in config:
                config[guild_id] = {}
            config[guild_id]["autorole_id"] = role.id
            save_config(config)
            await interaction.response.send_message(f"✅ Đã thiết lập Auto-Role! Từ giờ ai vào Server sẽ tự động được nhận vai trò {role.mention}.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Lỗi khi lưu Auto-Role: {e}", ephemeral=True)

    @app_commands.command(name="clear_autorole", description="Tắt tính năng tự động cấp vai trò cho thành viên mới")
    async def clear_autorole(self, interaction: discord.Interaction):
        user_perms = interaction.user.guild_permissions
        if not (user_perms.administrator or user_perms.manage_guild or user_perms.manage_roles):
            await interaction.response.send_message("❌ Mày phải có quyền Quản trị viên (Admin) mới được dùng lệnh này!", ephemeral=True)
            return

        config = load_config()
        guild_id = str(interaction.guild_id)
        if guild_id in config and "autorole_id" in config[guild_id]:
            del config[guild_id]["autorole_id"]
            save_config(config)
        await interaction.response.send_message("✅ Đã tắt tính năng tự động cấp vai trò!", ephemeral=True)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        config = load_config()
        guild_id = str(member.guild.id)
        
        # 1. Tự động cấp Role cho thành viên mới nếu có cài đặt
        autorole_id = config.get(guild_id, {}).get("autorole_id")
        if autorole_id:
            role = member.guild.get_role(autorole_id)
            if role:
                try:
                    await member.add_roles(role, reason="Auto-Role khi gia nhập server")
                except (discord.Forbidden, discord.HTTPException):
                    pass

        # 2. Gửi tin nhắn chào mừng bựa
        channel_id = config.get(guild_id, {}).get("welcome_channel_id")
        channel = member.guild.get_channel(channel_id) if channel_id else member.guild.system_channel
        if channel:
            msg = random.choice(self.join_messages).format(tag=member.mention)
            try:
                await channel.send(msg)
            except (discord.Forbidden, discord.HTTPException):
                pass

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        config = load_config()
        guild_id = str(member.guild.id)
        channel_id = config.get(guild_id, {}).get("welcome_channel_id")
        
        channel = member.guild.get_channel(channel_id) if channel_id else member.guild.system_channel
        if channel:
            msg = random.choice(self.leave_messages).format(name=member.display_name)
            try:
                await channel.send(msg)
            except (discord.Forbidden, discord.HTTPException):
                pass

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        # 1. Khi có người VÀO Voice
        if before.channel is None and after.channel is not None:
            msg = random.choice(self.vc_join_messages).format(mention=member.mention)
            try:
                await after.channel.send(msg)
            except (discord.Forbidden, AttributeError, discord.HTTPException):
                pass

        # 2. Khi có người RỜI Voice
        elif before.channel is not None and after.channel is None:
            msg = random.choice(self.vc_leave_messages).format(mention=member.mention)
            try:
                await before.channel.send(msg)
            except (discord.Forbidden, AttributeError, discord.HTTPException):
                pass


async def setup(bot):
    await bot.add_cog(Welcome(bot))
