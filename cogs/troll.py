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

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DEBTS_FILE = os.path.join(DATA_DIR, "debts.json")
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")

CLOWN_ICON_URL = "https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/72x72/1f921.png"
SCROLL_ICON_URL = "https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/72x72/1f4dc.png"

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
        if interaction.user.id not in [self.debtor.id, self.creditor.id]:
            await interaction.response.send_message("Mày không có quyền bấm nút này nha con!", ephemeral=True)
            return
        
        self.remove_debt()
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(content=f"✅ {self.debtor.mention} đã trả xong **{self.amount}k** tiền **{self.reason}** cho {self.creditor.mention}.", embed=None, view=self)

    @discord.ui.button(label="🔴 Chưa thấy tiền, đòi tiếp!", style=discord.ButtonStyle.danger)
    async def urge_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.creditor.id:
            await interaction.response.send_message("Chỉ chủ nợ mới được đòi tiếp!", ephemeral=True)
            return
        
        msg = f"😡 Alo {self.debtor.mention}, mày định quỵt luôn à? Chuyển ngay **{self.amount}k** tiền **{self.reason}** mau!"
        try:
            await interaction.channel.send(msg)
        except Exception:
            await interaction.followup.send(msg)
        await interaction.response.send_message("Đã chửi con nợ thành công!", ephemeral=True)

    @discord.ui.button(label="💀 Xóa nợ vì mày quá nghèo", style=discord.ButtonStyle.secondary)
    async def forgive_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.creditor.id:
            await interaction.response.send_message("Chỉ chủ nợ mới được phép bố thí!", ephemeral=True)
            return
        
        self.remove_debt()
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(content=f"💀 Tội nghiệp {self.debtor.mention} quá nghèo rách mồng tơi, {self.creditor.mention} đã từ bi hỉ xả xóa nợ **{self.amount}k** tiền **{self.reason}** như một ân huệ.", embed=None, view=self)


class NemDaModal(discord.ui.Modal, title='Ném đá giấu tay'):
    confession = discord.ui.TextInput(
        label='Nội dung muốn ném đá:',
        style=discord.TextStyle.paragraph,
        placeholder='Gõ những lời cay đắng vào đây...',
        required=True,
        max_length=1000
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message('Đã gửi thành công, không ai biết là mày đâu 🤫', ephemeral=True)
        
        names = ['Kẻ giấu mặt 🥷', 'Ninja làng Lá 🍃', 'Bóng ma học đường 👻']
        author_name = random.choice(names)
        
        embed = discord.Embed(
            title="📜 Thư nặc danh bí mật",
            description=self.confession.value,
            color=discord.Color.dark_gray()
        )
        embed.set_author(name=author_name)
        
        try:
            if interaction.channel:
                await interaction.channel.send(embed=embed)
            else:
                await interaction.followup.send(embed=embed)
        except discord.Forbidden:
            await interaction.followup.send(embed=embed)


class TrollCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="hdsd", description="Xem cẩm nang hướng dẫn sử dụng toàn bộ lệnh của Bot")
    async def hdsd(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📖 CẨM NANG SỬ DỤNG BOT - CHÚA TỂ CÀ KHỊA 🤡",
            description="Chào mừng bạn đến với chuồng hề! Dưới đây là toàn bộ bí kíp để quậy phá và quản trị server.",
            color=discord.Color.purple()
        )
        
        embed.add_field(
            name="💸 1. Máy Đòi Nợ Mặt Dày",
            value="• `/doino @user <số_tiền> <lý_do>`: Ghi sổ nợ, tag con nợ kèm 3 nút tương tác.\n• `/so_no`: Xem bảng phong thần top nợ dai nhất server.",
            inline=False
        )
        
        embed.add_field(
            name="🛞 2. Quét Độ Lốp Dự Phòng",
            value="• `/checklop @user`: Đo độ simp / lụy tình từ 0% đến 100% kèm chẩn đoán.",
            inline=False
        )

        embed.add_field(
            name="🃏 3. Thả Joker & Hề Chúa",
            value="• `/joker @user <lý_do>`: Phong danh Nghệ sĩ Ưu tú Ngành Hề + tặng văn mẫu Joker.",
            inline=False
        )

        embed.add_field(
            name="🥷 4. Ném Đá Giấu Tay (Ẩn Danh)",
            value="• `/nemda`: Bật hộp thoại bí mật để bóc phốt nặc danh. Không ai biết bạn là ai!",
            inline=False
        )

        embed.add_field(
            name="📢 5. Réo Tên Vong Hồn (Spam Tag)",
            value="• `/spamtag @user <nội_dung> <số_lần>`: Spam tag réo tên liên tục (max 10 lần, cooldown 45s).",
            inline=False
        )

        embed.add_field(
            name="📜 6. Luật & Nội Quy Server",
            value="• `/rule`: Xem 10 điều luật sinh tồn bất thành văn của Server.\n• `/set_rule <nội_dung>`: Admin cài đặt nội quy riêng cho lớp.",
            inline=False
        )

        embed.add_field(
            name="🔊 7. Chị Google Đọc Hộ Trong Voice",
            value="• `/join`: Mời chị Google vào phòng voice bạn đang ngồi.\n• `/noi <nội_dung>`: Chị Google đọc to văn bản bằng tiếng Việt.\n• `/leave`: Cho chị Google rời phòng.",
            inline=False
        )

        embed.add_field(
            name="⚙️ 8. Quản Trị & Cài Đặt (Admin)",
            value="• `/set_autorole @role`: Tự động cấp vai trò cho thành viên mới khi vào Server.\n• `/clear_autorole`: Tắt tự động cấp vai trò.\n• `/set_welcome #channel`: Chỉ định kênh gửi thông báo chào đón/tiễn.",
            inline=False
        )

        embed.set_footer(text="Gõ / để xem danh sách lệnh gợi ý trực tiếp của Discord!")
        embed.set_thumbnail(url=CLOWN_ICON_URL)
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="rule", description="Xem nội quy & 10 điều luật bất thành văn của Server")
    async def rule(self, interaction: discord.Interaction):
        config = load_json(CONFIG_FILE)
        guild_id = str(interaction.guild_id)
        custom_rule = config.get(guild_id, {}).get("custom_rule")

        embed = discord.Embed(
            title="📜 10 ĐIỀU LUẬT BẤT THÀNH VĂN CỦA CHUỒNG HỀ 🤡",
            color=discord.Color.gold()
        )

        if custom_rule:
            embed.description = f"**📢 NỘI QUY RIÊNG CỦA SERVER:**\n{custom_rule}\n\n" + "—"*25 + "\n**⚖️ 10 ĐIỀU LUẬT CỐT LÕI:**"
        else:
            embed.description = "Bất kỳ ai bước chân vào Server đều phải tuân thủ nghiêm ngặt các điều khoản sau:"

        rules_list = [
            "**Điều 1:** Cấm làm lốp xe dự phòng quá 24h. Bị phát hiện sẽ bị phạt lệnh `/checklop` công khai.",
            "**Điều 2:** Vay tiền không trả thì xác định ăn `/doino` cả ngày lẫn đêm đến khi nào trả mới thôi.",
            "**Điều 3:** Cấm sủi Voice không lý do (đặc biệt là lý do 'đi ăn cơm' xong mất tích 3 ngày).",
            "**Điều 4:** Phát ngôn ngáo ngơ, tự luyến tự giác nhận danh hiệu Joker 🃏.",
            "**Điều 5:** Nghiêm cấm chụp màn hình mang đi mách cô giáo hoặc phụ huynh.",
            "**Điều 6:** Tôn trọng chủ phòng Voice, không tranh mic rên rỉ giờ thi cử.",
            "**Điều 7:** Ai bị tag 10 lần bằng `/spamtag` mà không rep sẽ bị coi là 'Đáy xã hội'.",
            "**Điều 8:** Không dùng `/nemda` vu khống người vô tội (trừ khi thấy vui).",
            "**Điều 9:** Lời nói không mất tiền mua, lựa lời mà chửi cho vừa lòng nhau.",
            "**Điều 10:** Mọi quyết định của Admin là chân lý. Nếu Admin sai, xem lại Điều 1."
        ]

        embed.add_field(name="⚖️ Nội quy chi tiết", value="\n\n".join(rules_list), inline=False)
        embed.set_footer(text="Admin có thể dùng /set_rule để thêm nội quy riêng!")
        embed.set_thumbnail(url=SCROLL_ICON_URL)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="set_rule", description="Cài đặt nội quy riêng của Server (Dành cho Admin)")
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

    @app_commands.command(name="nemda", description="Ném đá giấu tay (Gửi ẩn danh)")
    async def nemda(self, interaction: discord.Interaction):
        await interaction.response.send_modal(NemDaModal())

    @app_commands.command(name="spamtag", description="Spam tag nhắc nhở một người")
    @app_commands.checks.cooldown(1, 45.0, key=lambda i: i.user.id)
    async def spamtag(self, interaction: discord.Interaction, user: discord.Member, noi_dung: str, so_lan: app_commands.Range[int, 1, 10]):
        prefixes = [
            "Dậy đi ông cháu ơi {tag}!",
            "Alo {tag} sủa lên xem nào?",
            "Hiện hồn về rep tin nhắn ngay {tag}!",
            "{tag} mày chết à mà không trả lời?"
        ]
        
        await interaction.response.send_message(f"⚡ Bắt đầu quy trình réo tên {user.mention} ({so_lan} lần)...", ephemeral=True)
        
        for _ in range(so_lan):
            prefix = random.choice(prefixes).format(tag=user.mention)
            msg_content = f"{prefix} - {noi_dung}"
            try:
                if interaction.channel:
                    await interaction.channel.send(msg_content)
                else:
                    await interaction.followup.send(msg_content)
            except discord.Forbidden:
                # Nếu bot bị thiếu quyền send trong kênh, fallback qua followup webhook
                await interaction.followup.send(msg_content)
            except Exception:
                await interaction.followup.send(msg_content)
            await asyncio.sleep(1.2)


async def setup(bot):
    await bot.add_cog(TrollCog(bot))
