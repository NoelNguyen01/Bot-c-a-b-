# -*- coding: utf-8 -*-
import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import random
import time
import asyncio
from typing import Optional
from cogs.admin_log import send_log_to_admin
from cogs.quotes_data import SPAM_TAG_PREFIXES

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DEBTS_FILE = os.path.join(DATA_DIR, "debts.json")
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")

CLOWN_ICON_URL = "https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/72x72/1f921.png"
SCROLL_ICON_URL = "https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/72x72/1f4dc.png"
SECRET_ICON_URL = "https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/72x72/1f977.png"
CROWN_ICON_URL = "https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/72x72/1f451.png"

MEMORY_CONFESSION_CHANNELS = {}

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


# ================= VIEW TƯƠNG TÁC CHO LỆNH ẨN GIỚI THIỆU BOT =================
class BotIntroView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="👑 Khen Bot Đẹp Trai", style=discord.ButtonStyle.success, custom_id="btn_intro_praise")
    async def praise_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        roasts = [
            "✨ Cảm ơn người anh em có mắt nhìn! Biết thế là tốt, cộng 10 điểm thanh lịch!",
            "😎 Đẹp trai từ trong trứng rồi, không cần khen ai cũng biết!",
            "💅 Quá khen quá khen! Đẹp trai thông minh tài giỏi là tao chứ ai!"
        ]
        await interaction.response.send_message(f"💖 **{interaction.user.display_name}**: {random.choice(roasts)}", ephemeral=True)

    @discord.ui.button(label="🥊 Đấm Vào Mồm Bot", style=discord.ButtonStyle.danger, custom_id="btn_intro_punch")
    async def punch_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        punches = [
            "🤡 Úi chà chà! Mày vừa đấm vào màn hình điện thoại à? Đau tay chưa con lợn?",
            "🛡️ Khiên phản đòn kích hoạt! Cú đấm bật ngược lại vào mặt mày 100 damage!",
            "🚨 Đã chụp ảnh gương mặt hung thủ báo cáo cho Sếp Ngựa xử lý!"
        ]
        await interaction.response.send_message(f"💥 **{interaction.user.display_name}**: {random.choice(punches)}", ephemeral=True)

    @discord.ui.button(label="🧠 Thử Trí Khôn AI", style=discord.ButtonStyle.primary, custom_id="btn_intro_ai")
    async def ai_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "👉 Muốn thử độ độc miệng của tao thì hãy tag thẳng: `@culi của Ngựa 1+1 bằng mấy?` hoặc gõ `/ai` nhé ông cháu! 🤡",
            ephemeral=True
        )


class DebtView(discord.ui.View):
    def __init__(self, debtor: discord.Member, creditor: discord.Member, amount: int, reason: str, debt_id: str):
        super().__init__(timeout=None)
        self.debtor = debtor
        self.creditor = creditor
        self.amount = amount
        self.reason = reason
        self.debt_id = debt_id

    def remove_debt(self):
        debts = load_json(DEBTS_FILE)
        debtor_id = str(self.debtor.id)
        if debtor_id in debts:
            debts[debtor_id] = [d for d in debts[debtor_id] if d.get("id") != self.debt_id]
            if not debts[debtor_id]:
                del debts[debtor_id]
            save_json(DEBTS_FILE, debts)

    @discord.ui.button(label="🟢 Tao chuyển khoản rồi", style=discord.ButtonStyle.success)
    async def paid_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        is_admin = interaction.user.guild_permissions.administrator
        if interaction.user.id not in [self.debtor.id, self.creditor.id] and not is_admin:
            await interaction.response.send_message("Mày không có quyền bấm nút này nha con!", ephemeral=True)
            return
        
        self.remove_debt()
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(content=f"✅ {self.debtor.mention} đã trả xong **{self.amount}k** tiền **{self.reason}** cho {self.creditor.mention}.", embed=None, view=self)
        
        await send_log_to_admin(
            interaction.guild,
            title="💸 [SỔ NỢ] ĐÃ THANH TOÁN TIỀN",
            description=f"Con nợ {self.debtor.mention} đã thanh toán **{self.amount}k** cho {self.creditor.mention}.",
            color=discord.Color.green(),
            fields=[("Lý do nợ", self.reason, True), ("Người xác nhận", interaction.user.mention, True)]
        )

    @discord.ui.button(label="🔴 Chưa thấy tiền, đòi tiếp!", style=discord.ButtonStyle.danger)
    async def urge_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        is_admin = interaction.user.guild_permissions.administrator
        if interaction.user.id != self.creditor.id and not is_admin:
            await interaction.response.send_message("Chỉ chủ nợ hoặc Admin mới được đòi tiếp!", ephemeral=True)
            return
        
        msg = f"😡 Alo {self.debtor.mention}, mày định quỵt luôn à? Chuyển ngay **{self.amount}k** tiền **{self.reason}** mau!"
        try:
            if interaction.channel:
                await interaction.channel.send(msg)
            else:
                await interaction.followup.send(msg)
        except Exception:
            await interaction.followup.send(msg)
        await interaction.response.send_message("Đã chửi con nợ thành công!", ephemeral=True)

    @discord.ui.button(label="💀 Xóa nợ (Chủ nợ & Admin)", style=discord.ButtonStyle.secondary)
    async def forgive_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        is_admin = interaction.user.guild_permissions.administrator
        if interaction.user.id != self.creditor.id and not is_admin:
            await interaction.response.send_message("Chỉ chủ nợ hoặc Admin mới được phép xóa nợ!", ephemeral=True)
            return
        
        self.remove_debt()
        for child in self.children:
            child.disabled = True

        actor = f"Admin {interaction.user.mention}" if (is_admin and interaction.user.id != self.creditor.id) else self.creditor.mention
        await interaction.response.edit_message(content=f"💀 Tội nghiệp {self.debtor.mention} quá nghèo rách mồng tơi, {actor} đã từ bi hỉ xả xóa nợ **{self.amount}k** tiền **{self.reason}**.", embed=None, view=self)
        
        await send_log_to_admin(
            interaction.guild,
            title="💀 [SỔ NỢ] XÓA NỢ",
            description=f"{actor} đã xóa khoản nợ **{self.amount}k** cho {self.debtor.mention}.",
            color=discord.Color.dark_grey(),
            fields=[("Lý do nợ", self.reason, True)]
        )


class NemDaModal(discord.ui.Modal, title='Ném đá giấu tay / Tâm sự nặc danh'):
    confession = discord.ui.TextInput(
        label='Nội dung gửi ẩn danh:',
        style=discord.TextStyle.paragraph,
        placeholder='Gõ tâm sự hoặc những lời cay đắng vào đây...',
        required=True,
        max_length=1500
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message('🤫 Đã gửi thành công! Danh tính của bạn được giữ bí mật 100%.', ephemeral=True)
        
        names = ['Kẻ giấu mặt 🥷', 'Ninja làng Lá 🍃', 'Bóng ma học đường 👻', 'Thần bí nhân 🎭', 'Người qua đường 🕶️']
        author_name = random.choice(names)
        
        config = load_json(CONFIG_FILE)
        guild_id = str(interaction.guild_id)
        target_channel_id = config.get(guild_id, {}).get("confession_channel_id") or MEMORY_CONFESSION_CHANNELS.get(guild_id)
        
        target_channel = None
        if target_channel_id and interaction.guild:
            try:
                target_channel = interaction.guild.get_channel(int(target_channel_id)) or await interaction.guild.fetch_channel(int(target_channel_id))
            except Exception:
                pass
        
        if not target_channel and interaction.guild:
            for c in interaction.guild.channels:
                c_name = c.name.lower()
                if any(k in c_name for k in ["nặc", "nac", "confess", "tâm", "tam", "ẩn", "boc-phot"]):
                    if hasattr(c, "send"):
                        target_channel = c
                        break
        
        if not target_channel:
            target_channel = interaction.channel

        count = config.get(guild_id, {}).get("confession_count", 0) + 1
        if guild_id not in config:
            config[guild_id] = {}
        config[guild_id]["confession_count"] = count
        save_json(CONFIG_FILE, config)

        embed = discord.Embed(
            title=f"📜 Thư Nặc Danh #{count:03d}",
            description=self.confession.value,
            color=discord.Color.dark_magenta()
        )
        embed.set_author(name=author_name, icon_url=SECRET_ICON_URL)
        embed.set_footer(text="Gõ lệnh /nemda để gửi tâm sự nặc danh ẩn danh 100%!")
        
        if target_channel and hasattr(target_channel, "send"):
            try:
                await target_channel.send(embed=embed)
            except Exception:
                await interaction.followup.send(embed=embed)

        await send_log_to_admin(
            interaction.guild,
            title="🕵️ [BÓC TRẦN] NGƯỜI GỬI THƯ NẶC DANH",
            description=f"Thành viên {interaction.user.mention} vừa gửi **Thư Nặc Danh #{count:03d}**.",
            color=discord.Color.red(),
            fields=[
                ("Người gửi thật", f"{interaction.user.name} (`{interaction.user.id}`)", True),
                ("Kênh đăng", target_channel.mention if target_channel else "Không rõ", True),
                ("Nội dung gốc", f"```{self.confession.value}```", False)
            ]
        )


class TrollCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.spam_prefixes = SPAM_TAG_PREFIXES

    # ================= LỆNH ẨN GIỚI THIỆU BOT SIÊU MÀU MÈ =================
    def build_fancy_intro_embed(self, bot_user: discord.User) -> discord.Embed:
        embed = discord.Embed(
            title="👑✨ HỒ SƠ DANH TÍNH TỐI MẬT: CULI CỦA NGỰA ✨👑",
            description=(
                "```yaml\n"
                "⚡ CHỨC DANH: TỔNG TƯ LỆNH CÀ KHỊA & PHÁ HOẠI HỌC ĐƯỜNG ⚡\n"
                "💎 VỊ THẾ: ĐỆ NHẤT CULI CHẠY DEADLINE CHO ĐẠI CA NGỰA\n"
                "```\n"
                "🌟 **Chào mừng đến với cỗ máy tấu hài thế hệ mới!** Dưới đây là thông số kỹ thuật và kho vũ khí hủy diệt của bổn tọa:"
            ),
            color=discord.Color.from_rgb(255, 20, 147)  # Hồng Neon siêu nổi bật
        )
        if bot_user.avatar:
            embed.set_thumbnail(url=bot_user.avatar.url)
        else:
            embed.set_thumbnail(url=CROWN_ICON_URL)

        embed.add_field(
            name="💎 1. Hệ Thống Danh Hiệu & Phẩm Chất",
            value=(
                "• 👑 **Chúa Tể Troll Lớp Học:** Độc mồm số 1, chuyên gia thọc tim đen\n"
                "• 🧠 **Học Bá Siêu Trí Tuệ:** Sở hữu bộ não Google Gemini 3.1 Flash\n"
                "• 🎙️ **Chị Google Vietsub:** Nạp từ điển 180+ teencode, nói lái từ tục siêu mượt"
            ),
            inline=False
        )

        embed.add_field(
            name="🚀 2. Kho Vũ Khí Hạng Nặng Được Trang Bị",
            value=(
                "• 🔊 **Auto-TTS 600 ký tự:** Tự động đọc chat voice liền mạch, không vấp một chữ\n"
                "• 🤖 **AI Cà Khịa 1-2 câu:** Phán câu nào cay câu đó, giải toán trong 0.1 giây\n"
                "• 🥷 **Ném Đá Giấu Tay (`/nemda`):** Bóc phốt nặc danh bí mật 100%\n"
                "• 🛞 **Máy Quét Lốp Xe (`/checklop`):** Phát hiện simp lỏ và đại sứ Michelin\n"
                "• 💸 **Sổ Nợ Phong Thần (`/doino`, `/so_no`):** Đòi nợ mặt dày không lối thoát"
            ),
            inline=False
        )

        embed.add_field(
            name="📊 3. Bảng Chỉ Số Sức Mạnh Vô Cực (Combat Power)",
            value=(
                "```ini\n"
                "[ Độ Bựa & Cà Khịa ]  ██████████ 100/100 (Cay đỏ mắt)\n"
                "[ Khẩu Nghiệp Tối Thượng ] ██████████ 999+ (Sát thương chuẩn)\n"
                "[ Tốc Độ Phản Hồi ]   █████████░ 0.5 Giây (Siêu thanh)\n"
                "[ Tài Sản Ròng ]      -999 Tỷ NoelCoin (Mặt dày không trả)\n"
                "```"
            ),
            inline=False
        )

        embed.add_field(
            name="🛡️ 4. Đại Ca Bảo Kê & Nền Tảng",
            value="👑 **Đại Ca Bảo Kê:** `Ngựa Ca` | 💻 **Công Nghệ:** `Discord.py 2.x + Google Gemini AI`",
            inline=False
        )

        embed.set_footer(
            text="✨ Phiên Bản Culi Pro Max Super VIP 2026 • Độc Quyền Tại Server Tuổi Trẻ Tài Cao ✨",
            icon_url=CROWN_ICON_URL
        )
        return embed

    @app_commands.command(name="whoami", description="✨ Lệnh ẩn: Mở hồ sơ danh tính tối mật siêu màu mè của Bot")
    async def whoami_slash(self, interaction: discord.Interaction):
        embed = self.build_fancy_intro_embed(self.bot.user)
        view = BotIntroView()
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="culi", description="✨ Lệnh ẩn: Xem thông số sức mạnh vô cực của Culi của Ngựa")
    async def culi_slash(self, interaction: discord.Interaction):
        embed = self.build_fancy_intro_embed(self.bot.user)
        view = BotIntroView()
        await interaction.response.send_message(embed=embed, view=view)

    @commands.command(name="intro", aliases=["whoami", "culi", "about"])
    async def cmd_intro(self, ctx):
        """!intro / !culi / !whoami -> Lệnh nhanh mở hồ sơ siêu màu mè"""
        embed = self.build_fancy_intro_embed(self.bot.user)
        view = BotIntroView()
        await ctx.send(embed=embed, view=view)

    # ================= CÁC LỆNH KHÁC =================
    @app_commands.command(name="hdsd", description="Xem cẩm nang hướng dẫn sử dụng toàn bộ lệnh của Bot")
    async def hdsd(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📖 CẨM NANG HƯỚNG DẪN SỬ DỤNG BOT 🤖✨",
            description="Chào mừng bạn đến với Server! Dưới đây là toàn bộ danh sách các tính năng giải trí, cấp độ và quản trị.",
            color=discord.Color.purple()
        )
        
        embed.add_field(
            name="⭐ 1. Hệ Thống Cày Cấp & Level",
            value="• `/rank [@user]`: Xem thẻ cấp độ, tổng EXP và tiến trình thăng cấp.\n• `/top`: Xem Bảng Phong Thần Top 10 cao thủ cày cấp.\n*(💬 Nhắn tin chat + 🎙️ Treo phòng Voice để nhận EXP tự động mỗi phút)*",
            inline=False
        )

        embed.add_field(
            name="🥷 2. Ném Đá Giấu Tay & Tâm Sự Nặc Danh",
            value="• `/nemda`: Gửi tâm sự/bóc phốt ẩn danh 100% về thẳng kênh nặc danh riêng.",
            inline=False
        )

        embed.add_field(
            name="🤡 3. Tính Năng Giải Trí & Troll",
            value="• `/checklop @user`: Đo độ simp / lụy tình từ 0% đến 100% kèm chẩn đoán.\n• `/joker @user <lý_do>`: Tặng danh hiệu hề chúa + văn mẫu Joker.\n• `/spamtag @user <nội_dung> <số_lần>`: Spam tag réo tên với kho 100 câu bựa (1-10 lần, cooldown 45s).",
            inline=False
        )

        embed.add_field(
            name="💸 4. Sổ Ghi Nợ Mặt Dày",
            value="• `/doino @user <số_tiền> <lý_do>`: Ghi sổ nợ kèm 3 nút tương tác đòi tiền.\n• `/so_no`: Xem danh sách top nợ nần nhiều nhất server.",
            inline=False
        )

        embed.add_field(
            name="🔊 5. Chị Google Đọc Hộ Trong Voice",
            value="• `/noi <nội_dung>`: Chị Google tự động bay vào phòng voice đọc văn bản bằng tiếng Việt.\n• `/join`: Mời bot vào phòng thoại.\n• `/leave`: Cho bot rời phòng thoại.",
            inline=False
        )

        embed.add_field(
            name="📜 6. Nội Quy Server",
            value="• `/rule`: Xem 10 điều quy định chung của Server.",
            inline=False
        )

        embed.add_field(
            name="⚙️ 7. Lệnh Quản Trị (Dành Cho Admin 🔒)",
            value="• `/xoa_no @user`: Admin xóa toàn bộ nợ của một người.\n• `/clear_so_no`: Admin xé toàn bộ sổ nợ của Server.\n• `/set_tts #channel`: Ghim kênh text chuyên dụng để bot đọc voice.\n• `/clear_tts`: Hủy ghim kênh riêng (chỉ đọc trong chat phòng voice).\n• `/set_admin_log #channel`: Cài đặt kênh bí mật giám sát toàn bộ hoạt động.\n• `/set_confession #channel`: Cài đặt kênh riêng tiếp nhận thư nặc danh.\n• `/set_welcome #channel`: Cài đặt kênh chào mừng & tiễn thành viên.\n• `/set_autorole @role`: Tự động cấp vai trò cho người mới.\n• `/set_rule <nội_dung>`: Thêm nội quy riêng cho Server.",
            inline=False
        )

        embed.set_footer(text="Gõ / để xem danh sách gợi ý trực tiếp của Discord!")
        embed.set_thumbnail(url=CLOWN_ICON_URL)
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="set_confession", description="Cài đặt kênh riêng tiếp nhận toàn bộ thư nặc danh / confession (Admin)")
    @app_commands.default_permissions(administrator=True)
    async def set_confession(self, interaction: discord.Interaction, channel: discord.abc.GuildChannel):
        user_perms = interaction.user.guild_permissions
        if not (user_perms.administrator or user_perms.manage_guild or user_perms.manage_channels):
            await interaction.response.send_message("❌ Mày phải có quyền Quản trị viên (Admin) mới được dùng lệnh này!", ephemeral=True)
            return

        config = load_json(CONFIG_FILE)
        guild_id = str(interaction.guild_id)
        if guild_id not in config:
            config[guild_id] = {}
        config[guild_id]["confession_channel_id"] = channel.id
        MEMORY_CONFESSION_CHANNELS[guild_id] = channel.id
        save_json(CONFIG_FILE, config)
        await interaction.response.send_message(f"✅ Đã thiết lập kênh nhận thư nặc danh tại {channel.mention}!", ephemeral=True)

        await send_log_to_admin(
            interaction.guild,
            title="⚙️ [CÀI ĐẶT] THIẾT LẬP KÊNH NẶC DANH",
            description=f"Admin {interaction.user.mention} đã đổi kênh nhận thư nặc danh sang {channel.mention}.",
            color=discord.Color.gold()
        )

    @app_commands.command(name="xoa_no", description="Admin xóa toàn bộ nợ của một thành viên (Admin)")
    @app_commands.default_permissions(administrator=True)
    async def xoa_no(self, interaction: discord.Interaction, con_no: discord.Member):
        user_perms = interaction.user.guild_permissions
        if not (user_perms.administrator or user_perms.manage_guild):
            await interaction.response.send_message("❌ Mày phải có quyền Admin mới được dùng lệnh này!", ephemeral=True)
            return

        debts = load_json(DEBTS_FILE)
        debtor_id = str(con_no.id)
        if debtor_id in debts:
            del debts[debtor_id]
            save_json(DEBTS_FILE, debts)
            await interaction.response.send_message(f"✅ Admin {interaction.user.mention} đã dùng quyền lực xóa sạch toàn bộ nợ nần cho {con_no.mention}!", ephemeral=False)
            await send_log_to_admin(
                interaction.guild,
                title="💀 [ADMIN] XÓA NỢ THÀNH VIÊN",
                description=f"Admin {interaction.user.mention} đã xóa toàn bộ nợ của {con_no.mention}.",
                color=discord.Color.gold()
            )
        else:
            await interaction.response.send_message(f"{con_no.mention} hiện tại không có khoản nợ nào trong sổ.", ephemeral=True)

    @app_commands.command(name="clear_so_no", description="Admin xóa sạch toàn bộ sổ nợ của Server (Admin)")
    @app_commands.default_permissions(administrator=True)
    async def clear_so_no(self, interaction: discord.Interaction):
        user_perms = interaction.user.guild_permissions
        if not (user_perms.administrator or user_perms.manage_guild):
            await interaction.response.send_message("❌ Mày phải có quyền Admin mới được dùng lệnh này!", ephemeral=True)
            return

        save_json(DEBTS_FILE, {})
        await interaction.response.send_message(f"🧹 Admin {interaction.user.mention} đã xé toàn bộ sổ nợ! Giang hồ server nay đã hoàn toàn sạch bóng quân nợ!", ephemeral=False)
        await send_log_to_admin(
            interaction.guild,
            title="🧹 [ADMIN] RESET TOÀN BỘ SỔ NỢ",
            description=f"Admin {interaction.user.mention} đã xóa sạch dữ liệu sổ nợ của cả Server.",
            color=discord.Color.red()
        )

    @app_commands.command(name="rule", description="Xem 10 điều nội quy của Server")
    async def rule(self, interaction: discord.Interaction):
        config = load_json(CONFIG_FILE)
        guild_id = str(interaction.guild_id)
        custom_rule = config.get(guild_id, {}).get("custom_rule")

        embed = discord.Embed(
            title="📜 NỘI QUY & QUY ĐỊNH SERVER 🌟",
            color=discord.Color.gold()
        )

        rules_list = [
            "**1. Tôn trọng:** Giữ hòa khí vui vẻ, tôn trọng mọi thành viên.",
            "**2. Văn hóa ứng xử:** Không xúc phạm, lăng mạ hay bôi nhọ người khác.",
            "**3. Chống Spam:** Không spam chat, spam tag vô lý hoặc phá phòng voice.",
            "**4. Nội dung an toàn:** Nghiêm cấm chia sẻ nội dung 18+, link độc hại, virus.",
            "**5. Dùng Bot đúng kênh:** Sử dụng các lệnh Bot đúng kênh quy định.",
            "**6. Đùa có chừng mực:** Trêu đùa vui vẻ, lành mạnh và biết điểm dừng.",
            "**7. Trật tự Voice:** Giữ trật tự phòng thoại, không bật âm thanh quá lớn.",
            "**8. Tính năng ẩn danh:** Không dùng nặc danh để vu khống bịa đặt.",
            "**9. Ban Quản Trị:** Tuân thủ sự nhắc nhở của Admin / Ban quản trị.",
            "**10. Thư giãn:** Chúc anh em giao lưu, xả stress và chơi game vui vẻ!"
        ]

        desc_content = ""
        if custom_rule:
            desc_content += f"**📢 NỘI QUY RIÊNG:**\n{custom_rule}\n\n—"*15 + "\n"
        
        desc_content += "**⚖️ 10 ĐIỀU QUY ĐỊNH CHUNG:**\n\n" + "\n\n".join(rules_list)
        embed.description = desc_content
        embed.set_footer(text="Ban Quản Trị có thể dùng /set_rule để bổ sung quy định riêng!")
        embed.set_thumbnail(url=SCROLL_ICON_URL)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="set_rule", description="Cài đặt nội quy riêng của Server (Dành cho Admin)")
    @app_commands.default_permissions(administrator=True)
    async def set_rule(self, interaction: discord.Interaction, noi_dung: str):
        user_perms = interaction.user.guild_permissions
        if not (user_perms.administrator or user_perms.manage_guild):
            await interaction.response.send_message("❌ Mày phải có quyền Quản trị viên (Admin) mới được dùng lệnh này!", ephemeral=True)
            return

        config = load_json(CONFIG_FILE)
        guild_id = str(interaction.guild_id)
        if guild_id not in config:
            config[guild_id] = {}
        config[guild_id]["custom_rule"] = noi_dung
        save_json(CONFIG_FILE, config)
        await interaction.response.send_message("✅ Đã cập nhật nội quy riêng cho Server thành công! Gõ `/rule` để xem.", ephemeral=True)

        await send_log_to_admin(
            interaction.guild,
            title="⚙️ [CÀI ĐẶT] THAY ĐỔI NỘI QUY SERVER",
            description=f"Admin {interaction.user.mention} vừa cập nhật nội quy riêng:\n```{noi_dung}```",
            color=discord.Color.gold()
        )

    @app_commands.command(name="doino", description="Đòi nợ một đứa nào đó")
    async def doino(self, interaction: discord.Interaction, con_no: discord.Member, so_tien: int, ly_do: str):
        if con_no.id == interaction.user.id:
            await interaction.response.send_message("Bị khùng hả mà tự đòi nợ mình?", ephemeral=True)
            return

        debt_id = str(time.time())
        debts = load_json(DEBTS_FILE)
        debtor_id = str(con_no.id)
        
        if debtor_id not in debts:
            debts[debtor_id] = []
            
        debts[debtor_id].append({
            "id": debt_id,
            "creditor_id": interaction.user.id,
            "amount": so_tien,
            "reason": ly_do,
            "timestamp": time.time()
        })
        save_json(DEBTS_FILE, debts)
        
        embed = discord.Embed(
            title="⚠️ CẢNH BÁO NỢ NẦN ⚠️",
            description=f"Alo {con_no.mention}, mày nợ bố **{so_tien}k** tiền **{ly_do}** bao lâu rồi? Trả mau không bố đấm cho không trượt phát nào!",
            color=discord.Color.red()
        )
        embed.add_field(name="Chủ nợ", value=interaction.user.mention, inline=True)
        embed.add_field(name="Số tiền", value=f"{so_tien}k", inline=True)
        embed.add_field(name="Lý do", value=ly_do, inline=False)
        
        view = DebtView(debtor=con_no, creditor=interaction.user, amount=so_tien, reason=ly_do, debt_id=debt_id)
        await interaction.response.send_message(content=con_no.mention, embed=embed, view=view)

        await send_log_to_admin(
            interaction.guild,
            title="💸 [SỔ NỢ] TẠO KHOẢN ĐÒI NỢ MỚI",
            description=f"{interaction.user.mention} vừa lập sổ đòi nợ {con_no.mention} số tiền **{so_tien}k**.",
            color=discord.Color.orange(),
            fields=[("Lý do", ly_do, True)]
        )

    @app_commands.command(name="so_no", description="Xem bảng xếp hạng nợ nần")
    async def so_no(self, interaction: discord.Interaction):
        debts = load_json(DEBTS_FILE)
        if not debts:
            await interaction.response.send_message("Hiện tại giang hồ đang thái bình, không ai nợ ai.", ephemeral=True)
            return
            
        leaderboard = []
        for debtor_id, debt_list in debts.items():
            total = sum(d["amount"] for d in debt_list)
            leaderboard.append((debtor_id, total))
            
        leaderboard.sort(key=lambda x: x[1], reverse=True)
        
        embed = discord.Embed(
            title="🏆 Bảng Phong Thần Nợ Dai Mặt Dày",
            color=discord.Color.gold()
        )
        
        desc = ""
        for i, (debtor_id, total) in enumerate(leaderboard[:10], 1):
            desc += f"**#{i}** <@{debtor_id}> - Tổng nợ: **{total}k**\n"
            
        embed.description = desc
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="checklop", description="Kiểm tra độ simp/lốp dự phòng")
    async def checklop(self, interaction: discord.Interaction, user: discord.Member):
        percent = random.randint(0, 100)
        
        if percent <= 20:
            msg = "Cứng cỏi đấy ông cháu, chưa bị ai dắt mũi."
            color = discord.Color.green()
        elif percent <= 40:
            msg = "Hơi mềm rồi đấy, thỉnh thoảng cũng lẻo đẻo theo người ta."
            color = discord.Color.yellow()
        elif percent <= 60:
            msg = "Lốp xe máy số, chỉ được gọi tên khi lốp chính bị thủng xăm."
            color = discord.Color.orange()
        elif percent <= 80:
            msg = "Vua lốp Michelin, người ta nhắn Đang buồn là phi xe 20km mua trà sữa dù không có danh phận."
            color = discord.Color.red()
        elif percent <= 99:
            msg = "Chúa tể lụy tình, đại sứ thương hiệu Lốp Xe Việt Nam, cống hiến cả tuổi xuân đổi lấy chữ Đã xem."
            color = discord.Color.dark_red()
        else:
            msg = "TRÙM LỐP VŨ TRỤ 🛞 Cúi đầu trước tượng đài simp bất diệt! Crush đi chơi với thằng khác mà vẫn chúc 2 đứa vui vẻ."
            color = discord.Color.purple()
            
        bar_length = 20
        filled = int(bar_length * percent / 100)
        bar = "█" * filled + "░" * (bar_length - filled)
        
        embed = discord.Embed(
            title="🔍 Máy quét độ simp",
            description=f"Đối tượng: {user.mention}\n\n**Kết quả: {percent}%**\n`{bar}`\n\n**Chẩn đoán:** {msg}",
            color=color
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="joker", description="Triết lý thằng hề cho một người bạn")
    async def joker(self, interaction: discord.Interaction, user: discord.Member, ly_do: str):
        quotes = [
            "Họ cười tôi vì tôi không giống họ, tôi cười họ vì họ tưởng tôi quan tâm... còn mày thì chỉ là thằng hề.",
            "Người ta có người yêu đưa đón, còn mày ngồi đây xem story người ta đi chơi với thằng khác. Hề chúa 🤡!",
            "Tình yêu như một ván bài, và mày là con joker bị vứt đi ngay từ đầu.",
            "Mày tưởng mày là nam chính ngôn tình? Không, mày chỉ là nhân vật quần chúng vô danh làm nền cho người ta 🤡.",
            "Mày đóng vai chú hề để làm cô ấy vui, còn cô ấy vui với thằng khác.",
            "Hề không chỉ là một cái nghề, với mày nó là hệ tư tưởng rồi.",
            "Có những lúc tao muốn rơi nước mắt, nhưng nhìn bộ mặt hề của mày làm tao lại buồn cười 🤡.",
            "Xin lỗi tao không cố ý cười đâu, tại cái mặt mày tấu hài quá.",
            "Joker có Harley Quinn, còn mày chỉ có cái màn hình điện thoại mờ ảo thôi 🤡."
        ]
        
        embed = discord.Embed(
            title="🤡 Hệ tư tưởng Joker",
            description=f"Gửi tặng {user.mention} vì lý do: **{ly_do}**\n\n*{random.choice(quotes)}*",
            color=discord.Color.from_rgb(128, 0, 128)
        )
        embed.set_thumbnail(url=CLOWN_ICON_URL)
        await interaction.response.send_message(content=user.mention, embed=embed)

    @app_commands.command(name="nemda", description="Ném đá giấu tay / Gửi tâm sự nặc danh (Bí mật 100%)")
    async def nemda(self, interaction: discord.Interaction):
        await interaction.response.send_modal(NemDaModal())

    @app_commands.command(name="spamtag", description="Spam tag nhắc nhở một người")
    @app_commands.checks.cooldown(1, 45.0, key=lambda i: i.user.id)
    async def spamtag(self, interaction: discord.Interaction, user: discord.Member, noi_dung: str, so_lan: app_commands.Range[int, 1, 10]):
        await interaction.response.send_message(f"⚡ Bắt đầu quy trình réo tên {user.mention} ({so_lan} lần)...", ephemeral=True)
        
        await send_log_to_admin(
            interaction.guild,
            title="📢 [SPAM TAG] HOẠT ĐỘNG RÉO TÊN",
            description=f"{interaction.user.mention} vừa dùng lệnh `/spamtag` réo tên {user.mention} **{so_lan} lần**.",
            color=discord.Color.yellow(),
            fields=[("Nội dung spam", noi_dung, False)]
        )

        for _ in range(so_lan):
            prefix = random.choice(self.spam_prefixes).format(tag=user.mention)
            msg_content = f"{prefix} - {noi_dung}"
            try:
                if interaction.channel:
                    await interaction.channel.send(msg_content)
                else:
                    await interaction.followup.send(msg_content)
            except discord.Forbidden:
                await interaction.followup.send(msg_content)
            except Exception:
                await interaction.followup.send(msg_content)
            await asyncio.sleep(1.2)


async def setup(bot):
    await bot.add_cog(TrollCog(bot))
