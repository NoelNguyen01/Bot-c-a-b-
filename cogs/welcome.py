# -*- coding: utf-8 -*-
import discord
from discord.ext import commands
from discord import app_commands
import random
import json
import os

CONFIG_FILE = "data/config.json"

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {}
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_config(data):
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
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
    @app_commands.checks.has_permissions(administrator=True)
    async def set_welcome(self, interaction: discord.Interaction, channel: discord.TextChannel):
        config = load_config()
        guild_id = str(interaction.guild_id)
        if guild_id not in config:
            config[guild_id] = {}
        config[guild_id]["welcome_channel_id"] = channel.id
        save_config(config)
        await interaction.response.send_message(f"✅ Đã cài đặt kênh chào mừng thành viên tại {channel.mention}!", ephemeral=True)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        config = load_config()
        guild_id = str(member.guild.id)
        channel_id = config.get(guild_id, {}).get("welcome_channel_id")
        
        channel = member.guild.get_channel(channel_id) if channel_id else member.guild.system_channel
        if channel:
            msg = random.choice(self.join_messages).format(tag=member.mention)
            try:
                await channel.send(msg)
            except discord.Forbidden:
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
            except discord.Forbidden:
                pass

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        # 1. Khi có người VÀO Voice
        if before.channel is None and after.channel is not None:
            msg = random.choice(self.vc_join_messages).format(mention=member.mention)
            try:
                # Gửi thẳng vào Text Chat của chính phòng Voice đó
                await after.channel.send(msg)
            except (discord.Forbidden, AttributeError):
                pass

        # 2. Khi có người RỜI Voice
        elif before.channel is not None and after.channel is None:
            msg = random.choice(self.vc_leave_messages).format(mention=member.mention)
            try:
                # Gửi thẳng vào Text Chat của chính phòng Voice đó
                await before.channel.send(msg)
            except (discord.Forbidden, AttributeError):
                pass


async def setup(bot):
    await bot.add_cog(Welcome(bot))
