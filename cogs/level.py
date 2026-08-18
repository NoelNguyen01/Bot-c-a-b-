# -*- coding: utf-8 -*-
import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import os
import time
import random
import logging
from typing import Optional

logger = logging.getLogger("LevelSystem")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
LEVELS_FILE = os.path.join(DATA_DIR, "levels.json")
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")

def load_json(filepath):
    if not os.path.exists(filepath):
        return {}
    with open(filepath, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_json(filepath, data):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def xp_for_level(level: int) -> int:
    """Tính tổng XP cần thiết để đạt level đó: XP = level^2 * 100"""
    return int((level ** 2) * 100)

def level_from_xp(xp: int) -> int:
    """Tính level tương ứng từ tổng số XP"""
    return int((xp / 100) ** 0.5)


class LevelCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.msg_cooldowns = {}  # { (guild_id, user_id): last_timestamp }
        self.voice_xp_loop.start()

    def cog_unload(self):
        self.voice_xp_loop.cancel()

    def add_xp(self, guild_id: int, user_id: int, xp_amount: int) -> tuple[int, int, bool]:
        """Cộng XP cho user. Trả về (old_level, new_level, has_leveled_up)"""
        levels = load_json(LEVELS_FILE)
        g_id = str(guild_id)
        u_id = str(user_id)

        if g_id not in levels:
            levels[g_id] = {}
        if u_id not in levels[g_id]:
            levels[g_id][u_id] = {"xp": 0}

        old_xp = levels[g_id][u_id].get("xp", 0)
        new_xp = old_xp + xp_amount
        levels[g_id][u_id]["xp"] = new_xp
        save_json(LEVELS_FILE, levels)

        old_level = level_from_xp(old_xp)
        new_level = level_from_xp(new_xp)
        return old_level, new_level, (new_level > old_level)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Bỏ qua tin nhắn từ Bot hoặc tin nhắn ngoài Server
        if message.author.bot or not message.guild:
            return

        user_id = message.author.id
        guild_id = message.guild.id
        now = time.time()

        # Cooldown cộng XP chat: 60s / lần để chống spam
        key = (guild_id, user_id)
        last_time = self.msg_cooldowns.get(key, 0)
        if now - last_time < 60:
            return

        self.msg_cooldowns[key] = now
        gained_xp = random.randint(15, 25)
        old_lvl, new_lvl, leveled_up = self.add_xp(guild_id, user_id, gained_xp)

        if leveled_up:
            embed = discord.Embed(
                title="🎉 THĂNG CẤP THÀNH VIÊN! 🆙",
                description=f"Chúc mừng {message.author.mention} vừa leo lên **Level {new_lvl}**!\nCày cuốc chăm chỉ đấy ông cháu! 🚀🔥",
                color=discord.Color.gold()
            )
            embed.set_thumbnail(url=message.author.display_avatar.url)
            try:
                await message.channel.send(content=message.author.mention, embed=embed)
            except Exception:
                pass

    @tasks.loop(minutes=1.0)
    async def voice_xp_loop(self):
        """Tự động cộng XP mỗi phút cho các thành viên đang treo phòng Voice"""
        await self.bot.wait_until_ready()
        
        for guild in self.bot.guilds:
            for vc in guild.voice_channels:
                # Chỉ cộng XP nếu phòng có từ 1 người trở lên và không phải bot
                real_members = [m for m in vc.members if not m.bot and not m.voice.self_deaf]
                for member in real_members:
                    gained_xp = random.randint(10, 20)
                    old_lvl, new_lvl, leveled_up = self.add_xp(guild.id, member.id, gained_xp)
                    
                    if leveled_up:
                        embed = discord.Embed(
                            title="🎙️ THĂNG CẤP BẰNG GIỌNG NÓI! 🆙",
                            description=f"Chúc mừng {member.mention} treo Voice đắc đạo lên **Level {new_lvl}**! 👑",
                            color=discord.Color.teal()
                        )
                        embed.set_thumbnail(url=member.display_avatar.url)
                        try:
                            await vc.send(content=member.mention, embed=embed)
                        except Exception:
                            pass

    @voice_xp_loop.before_loop
    async def before_voice_xp_loop(self):
        await self.bot.wait_until_ready()

    @app_commands.command(name="rank", description="Xem cấp độ (Level), điểm EXP và thứ hạng của bạn hoặc người khác")
    async def rank(self, interaction: discord.Interaction, user: Optional[discord.Member] = None):
        target = user or interaction.user
        guild_id = str(interaction.guild_id)
        user_id = str(target.id)

        levels = load_json(LEVELS_FILE)
        guild_levels = levels.get(guild_id, {})
        
        # Sắp xếp danh sách tính hạng
        sorted_users = sorted(guild_levels.items(), key=lambda x: x[1].get("xp", 0), reverse=True)
        
        rank_pos = "N/A"
        for i, (u_id, data) in enumerate(sorted_users, 1):
            if u_id == user_id:
                rank_pos = f"#{i}"
                break

        current_xp = guild_levels.get(user_id, {}).get("xp", 0)
        current_lvl = level_from_xp(current_xp)

        # Tính toán tiến trình XP trong level hiện tại
        xp_current_lvl_base = xp_for_level(current_lvl)
        xp_next_lvl_base = xp_for_level(current_lvl + 1)
        xp_needed_this_level = max(1, xp_next_lvl_base - xp_current_lvl_base)
        xp_progress_this_level = max(0, current_xp - xp_current_lvl_base)

        percent = min(100, int((xp_progress_this_level / xp_needed_this_level) * 100))
        
        bar_len = 16
        filled = int(bar_len * percent / 100)
        bar = "█" * filled + "░" * (bar_len - filled)

        embed = discord.Embed(
            title=f"📊 THẺ HỒ SƠ CẤP ĐỘ — {target.display_name}",
            color=discord.Color.purple()
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(name="🏆 Thứ hạng", value=f"**{rank_pos}** / {len(sorted_users)}", inline=True)
        embed.add_field(name="⭐ Cấp độ (Level)", value=f"**Level {current_lvl}**", inline=True)
        embed.add_field(name="✨ Tổng EXP", value=f"**{current_xp:,}** XP", inline=True)
        
        embed.add_field(
            name=f"📈 Tiến trình lên Level {current_lvl + 1} ({percent}%)",
            value=f"`{bar}`\n({xp_progress_this_level:,} / {xp_needed_this_level:,} XP)",
            inline=False
        )
        
        embed.set_footer(text="💬 Nhắn tin chat & 🎙️ Treo phòng Voice để nhận thêm EXP mỗi phút!")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="top", description="Xem Bảng Xếp Hạng Top 10 cao thủ cày cấp Level cao nhất Server")
    async def top(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild_id)
        levels = load_json(LEVELS_FILE)
        guild_levels = levels.get(guild_id, {})

        if not guild_levels:
            await interaction.response.send_message("Chưa có dữ liệu cày cấp nào trong Server. Hãy tích cực nhắn tin và treo Voice nhé!", ephemeral=True)
            return

        sorted_users = sorted(guild_levels.items(), key=lambda x: x[1].get("xp", 0), reverse=True)

        embed = discord.Embed(
            title="🏆 BẢNG PHONG THẦN CÀY CẤP (TOP LEADERBOARD) 🌟",
            description="Vinh danh những gương mặt vàng trong làng cày cuốc chat & voice của Server:",
            color=discord.Color.gold()
        )

        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        desc = ""
        
        for i, (u_id, data) in enumerate(sorted_users[:10]):
            xp = data.get("xp", 0)
            lvl = level_from_xp(xp)
            medal = medals[i] if i < len(medals) else f"#{i+1}"
            desc += f"{medal} <@{u_id}> — **Level {lvl}** `({xp:,} XP)`\n"

        embed.description = desc
        embed.set_footer(text="Gõ /rank để xem cấp độ của chính bạn!")
        
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(LevelCog(bot))
