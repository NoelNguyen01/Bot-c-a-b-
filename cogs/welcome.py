# -*- coding: utf-8 -*-
import discord
from discord.ext import commands
from discord import app_commands
import random
import json
import os
import logging

logger = logging.getLogger("Welcome")

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
        self.cache = load_config()
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

    def get_welcome_channel(self, guild: discord.Guild):
        guild_id = str(guild.id)
        config = load_config()
        channel_id = config.get(guild_id, {}).get("welcome_channel_id") or self.cache.get(guild_id, {}).get("welcome_channel_id")
        
        channel = None
        if channel_id:
            try:
                channel = guild.get_channel(int(channel_id))
            except Exception:
                pass

        # Nếu chưa cài đặt, tự động tìm kênh có tên hello-baibai, chao-mung, welcome
        if not channel:
            for c in guild.channels:
                if any(name in c.name.lower() for name in ["hello-baibai", "hello", "chao-mung", "welcome", "thong-bao"]):
                    if hasattr(c, "send"):
                        channel = c
                        break

        # Fallback cuối cùng về kênh hệ thống
        if not channel:
            channel = guild.system_channel
        return channel

    @app_commands.command(name="set_welcome", description="Cài đặt kênh gửi tin nhắn chào mừng/tiễn thành viên")
    async def set_welcome(
        self, 
        interaction: discord.Interaction, 
        channel: discord.abc.GuildChannel
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
            self.cache[guild_id] = config[guild_id]
            save_config(config)
            await interaction.response.send_message(f"✅ Đã ghim kênh chào mừng & tiễn thành viên tại {channel.mention}!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Lỗi khi lưu cài đặt: {e}", ephemeral=True)

    @app_commands.command(name="set_autorole", description="Cài đặt vai trò tự động cấp cho thành viên mới khi vào Server")
    async def set_autorole(self, interaction: discord.Interaction, role: discord.Role):
        user_perms = interaction.user.guild_permissions
        if not (user_perms.administrator or user_perms.manage_guild or user_perms.manage_roles):
            await interaction.response.send_message("❌ Mày phải có quyền Quản trị viên (Admin) hoặc Quản lý vai trò mới được dùng lệnh này nha!", ephemeral=True)
            return

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
            self.cache[guild_id] = config[guild_id]
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
            if guild_id in self.cache and "autorole_id" in self.cache[guild_id]:
                del self.cache[guild_id]["autorole_id"]
            save_config(config)
        await interaction.response.send_message("✅ Đã tắt tính năng tự động cấp vai trò!", ephemeral=True)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        logger.info(f"Thành viên mới vào server: {member.name} (ID: {member.id})")
        config = load_config()
        guild_id = str(member.guild.id)
        
        # 1. Tự động cấp Role cho thành viên mới nếu có cài đặt
        autorole_id = config.get(guild_id, {}).get("autorole_id") or self.cache.get(guild_id, {}).get("autorole_id")
        if autorole_id:
            try:
                role = member.guild.get_role(int(autorole_id))
                if role:
                    await member.add_roles(role, reason="Auto-Role khi gia nhập server")
                    logger.info(f"Đã cấp role {role.name} cho {member.name}")
            except Exception as e:
                logger.error(f"Lỗi cấp Auto-Role: {e}")

        # 2. Gửi tin nhắn chào mừng bựa
        channel = self.get_welcome_channel(member.guild)
        if channel and hasattr(channel, "send"):
            msg = random.choice(self.join_messages).format(tag=member.mention)
            try:
                await channel.send(msg)
                logger.info(f"Đã gửi thông báo chào mừng {member.name} vào kênh {channel.name}")
            except Exception as e:
                logger.error(f"Lỗi gửi tin nhắn chào mừng: {e}")

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        logger.info(f"Thành viên rời server: {member.name} (ID: {member.id})")
        channel = self.get_welcome_channel(member.guild)
        if channel and hasattr(channel, "send"):
            msg = random.choice(self.leave_messages).format(name=member.display_name)
            try:
                await channel.send(msg)
                logger.info(f"Đã gửi thông báo tiễn {member.name} vào kênh {channel.name}")
            except Exception as e:
                logger.error(f"Lỗi gửi tin nhắn tiễn biệt: {e}")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        # 1. Khi có người VÀO Voice
        if before.channel is None and after.channel is not None:
            if member.id == self.bot.user.id:
                return
            msg = random.choice(self.vc_join_messages).format(mention=member.mention)
            try:
                await after.channel.send(msg)
            except Exception:
                pass

        # 2. Khi có người RỜI Voice
        elif before.channel is not None and after.channel is None:
            if member.id == self.bot.user.id:
                return
            msg = random.choice(self.vc_leave_messages).format(mention=member.mention)
            try:
                await before.channel.send(msg)
            except Exception:
                pass


async def setup(bot):
    await bot.add_cog(Welcome(bot))
