# -*- coding: utf-8 -*-
import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import logging
from typing import Optional
from cogs.admin_log import send_log_to_admin

logger = logging.getLogger("Verify")

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


class VerifyButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="🔓 Bấm Vào Đây Để Mở Khóa Server",
            style=discord.ButtonStyle.success,
            emoji="✅",
            custom_id="persistent_btn_verify_member"
        )

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        member = interaction.user
        if not isinstance(member, discord.Member):
            try:
                member = await guild.fetch_member(interaction.user.id)
            except Exception:
                pass

        config = load_config()
        guild_id = str(guild.id)
        verify_role_id = config.get(guild_id, {}).get("verify_role_id")
        
        target_role = None
        if verify_role_id:
            target_role = guild.get_role(int(verify_role_id))

        # Tự động tìm vai trò 'mem bơ', 'Member', 'Thành Viên' nếu chưa gán
        if not target_role:
            for r in guild.roles:
                r_name = r.name.lower()
                if any(k in r_name for k in ["mem bơ", "mem", "thành viên", "thanh vien", "member", "verified"]):
                    target_role = r
                    break

        if not target_role:
            await interaction.response.send_message(
                "❌ Chưa cấu hình vai trò xác thực! Vui lòng nhờ Admin gõ `/set_verify_role @role` nhé.",
                ephemeral=True
            )
            return

        # Kiểm tra xem người này đã có role chưa
        if target_role in member.roles:
            await interaction.response.send_message(
                "✨ Bạn đã xác thực rồi nha! Hãy tận hưởng các kênh trong Server.",
                ephemeral=True
            )
            return

        # Kiểm tra quyền hạn thứ bậc role
        if target_role >= guild.me.top_role:
            await interaction.response.send_message(
                f"❌ Bot không đủ quyền cấp vai trò {target_role.mention} vì vai trò của Bot nằm dưới role này! Hãy nhờ Admin kéo role **culi của Ngựa** lên trên.",
                ephemeral=True
            )
            return

        try:
            # 1. Cấp role xác thực (ví dụ @mem bơ)
            await member.add_roles(target_role, reason="Xác thực thành công qua nút bấm")

            # 2. Xóa role tạm @No role nếu có
            no_roles = [r for r in member.roles if "no role" in r.name.lower() or "norole" in r.name.lower()]
            if no_roles:
                for nr in no_roles:
                    try:
                        await member.remove_roles(nr, reason="Đã xác thực, gỡ role No role")
                    except Exception:
                        pass

            await interaction.response.send_message(
                f"🎉 **XÁC THỰC THÀNH CÔNG!**\nBạn đã được nhận vai trò {target_role.mention} và mở khóa toàn bộ các kênh trong Server! Chúc bạn chơi vui vẻ! 🚀🥳",
                ephemeral=True
            )

            # 3. Gửi Nhật Ký Admin
            await send_log_to_admin(
                guild,
                title="✅ [XÁC THỰC] THÀNH VIÊN ĐÃ MỞ KHÓA SERVER",
                description=f"Thành viên {member.mention} vừa bấm nút xác thực.",
                color=discord.Color.green(),
                fields=[
                    ("Tên & ID", f"{member.name} (`{member.id}`)", True),
                    ("Vai trò đã nhận", target_role.mention, True)
                ]
            )
        except Exception as e:
            logger.error(f"Lỗi khi cấp role xác thực: {e}")
            await interaction.response.send_message(f"❌ Có lỗi xảy ra khi cấp vai trò: {e}", ephemeral=True)


class VerifyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(VerifyButton())


class VerifyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        # Đăng ký persistent view để nút bấm chạy 24/7 không bao giờ hết hạn
        self.bot.add_view(VerifyView())

    @app_commands.command(name="set_verify_role", description="Cài đặt vai trò sẽ được cấp khi thành viên bấm nút xác thực (Admin)")
    @app_commands.default_permissions(administrator=True)
    async def set_verify_role(self, interaction: discord.Interaction, role: discord.Role):
        user_perms = interaction.user.guild_permissions
        if not (user_perms.administrator or user_perms.manage_roles):
            await interaction.response.send_message("❌ Mày phải có quyền Admin mới được dùng lệnh này!", ephemeral=True)
            return

        config = load_config()
        guild_id = str(interaction.guild_id)
        if guild_id not in config:
            config[guild_id] = {}
        config[guild_id]["verify_role_id"] = role.id
        save_config(config)

        await interaction.response.send_message(
            f"✅ Đã thiết lập vai trò xác thực thành {role.mention}! Khi thành viên bấm nút xác thực, họ sẽ nhận được vai trò này.",
            ephemeral=True
        )

        await send_log_to_admin(
            interaction.guild,
            title="⚙️ [CÀI ĐẶT] ĐỔI VAI TRÒ XÁC THỰC",
            description=f"Admin {interaction.user.mention} đã đổi vai trò mở khóa sang {role.mention}.",
            color=discord.Color.gold()
        )

    @app_commands.command(name="send_verify", description="Gửi bảng tin xác thực kèm nút bấm mở khóa Server vào kênh (Admin)")
    @app_commands.default_permissions(administrator=True)
    async def send_verify(
        self,
        interaction: discord.Interaction,
        channel: discord.abc.GuildChannel,
        tieu_de: Optional[str] = "XÁC THỰC THÀNH VIÊN — MỞ KHÓA SERVER 🔓",
        noi_dung: Optional[str] = "Chào mừng bạn đến với Server! Vui lòng bấm vào nút bên dưới để xác thực danh tính và mở khóa toàn bộ các kênh trò chuyện."
    ):
        user_perms = interaction.user.guild_permissions
        if not (user_perms.administrator or user_perms.manage_channels):
            await interaction.response.send_message("❌ Mày phải có quyền Admin mới được dùng lệnh này!", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"🛡️ {tieu_de}",
            description=f"{noi_dung}\n\n👇 **Bấm nút màu xanh bên dưới để vào Server ngay:**",
            color=discord.Color.green()
        )
        embed.set_footer(text="Hệ Thống Xác Thực Tự Động 24/7 • Chúc bạn chơi vui vẻ!")
        embed.set_thumbnail(url="https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/72x72/1f510.png")

        try:
            if hasattr(channel, "send"):
                await channel.send(embed=embed, view=VerifyView())
                await interaction.response.send_message(f"✅ Đã gửi bảng tin xác thực thành công vào kênh {channel.mention}!", ephemeral=True)
            else:
                await interaction.response.send_message("❌ Kênh đã chọn không hỗ trợ gửi tin nhắn văn bản!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Lỗi khi gửi bảng xác thực: {e}", ephemeral=True)


async def setup(bot):
    await bot.add_cog(VerifyCog(bot))
