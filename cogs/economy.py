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

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
ECONOMY_FILE = os.path.join(DATA_DIR, "economy.json")

COIN_NAME = "NoelCoin"
COIN_SYM = "NC"
COIN_ICON = "🪙"

def load_economy():
    if not os.path.exists(ECONOMY_FILE):
        return {}
    with open(ECONOMY_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_economy(data):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(ECONOMY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


# ================= GIAO DIỆN XÌ DÁCH (BLACKJACK) VỚI NÚT BẤM =================
SUITS = ['♠️', '♥️', '♦️', '♣️']
RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']

def draw_card():
    return (random.choice(RANKS), random.choice(SUITS))

def card_to_str(card):
    return f"`{card[0]}{card[1]}`"

def calculate_hand(hand):
    val = 0
    aces = 0
    for rank, _ in hand:
        if rank in ['J', 'Q', 'K']:
            val += 10
        elif rank == 'A':
            aces += 1
            val += 11
        else:
            val += int(rank)
    while val > 21 and aces > 0:
        val -= 10
        aces -= 1
    return val


class BlackjackView(discord.ui.View):
    def __init__(self, cog, user: discord.Member, bet: int, player_hand: list, dealer_hand: list):
        super().__init__(timeout=60.0)
        self.cog = cog
        self.user = user
        self.bet = bet
        self.player_hand = player_hand
        self.dealer_hand = dealer_hand
        self.finished = False

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("❌ Bàn bài này không phải của bạn!", ephemeral=True)
            return False
        return True

    def build_embed(self, show_dealer: bool = False, outcome: str = "", color: discord.Color = discord.Color.blue()):
        p_val = calculate_hand(self.player_hand)
        p_cards = " ".join(card_to_str(c) for c in self.player_hand)

        if show_dealer:
            d_val = calculate_hand(self.dealer_hand)
            d_cards = " ".join(card_to_str(c) for c in self.dealer_hand)
            dealer_text = f"**Bài Nhà Cái:** {d_cards} `({d_val} điểm)`"
        else:
            dealer_text = f"**Bài Nhà Cái:** {card_to_str(self.dealer_hand[0])} `🂠` `(? điểm)`"

        embed = discord.Embed(
            title="🃏 SÒNG BẠC XÌ DÁCH (BLACKJACK) 🎰",
            description=f"**Người chơi:** {self.user.mention} | **Tiền cược:** **{self.bet:,} {COIN_SYM}**\n\n"
                        f"{dealer_text}\n"
                        f"**Bài Của Bạn:** {p_cards} `({p_val} điểm)`\n\n"
                        f"{outcome}",
            color=color
        )
        embed.set_footer(text="Bấm 'Rút Bài' để lấy thêm lá hoặc 'Dằn Bài' để so điểm!")
        return embed

    @discord.ui.button(label="🃏 Rút Bài (Hit)", style=discord.ButtonStyle.success)
    async def hit(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.finished:
            return

        self.player_hand.append(draw_card())
        p_val = calculate_hand(self.player_hand)

        if p_val > 21:
            self.finished = True
            for child in self.children:
                child.disabled = True
            
            self.cog.add_money(interaction.guild_id, self.user.id, -self.bet)
            new_bal = self.cog.get_balance(interaction.guild_id, self.user.id)
            
            embed = self.build_embed(
                show_dealer=True,
                outcome=f"💥 **BẠN ĐÃ BỊ QUẮC (> 21 điểm)!**\n💸 Bạn đã mất trắng **-{self.bet:,} {COIN_SYM}**! Số dư còn: **{new_bal:,} {COIN_SYM}**.",
                color=discord.Color.red()
            )
            await interaction.response.edit_message(embed=embed, view=self)
        elif len(self.player_hand) == 5:
            self.finished = True
            for child in self.children:
                child.disabled = True
            
            win_amt = int(self.bet * 1.5)
            self.cog.add_money(interaction.guild_id, self.user.id, win_amt)
            new_bal = self.cog.get_balance(interaction.guild_id, self.user.id)

            embed = self.build_embed(
                show_dealer=True,
                outcome=f"🌟 **NGŨ LINH THẦN THÁNH (5 LÁ <= 21 ĐIỂM)!**\n🎉 Bạn thắng lớn nhận **+{win_amt:,} {COIN_SYM}**! Số dư: **{new_bal:,} {COIN_SYM}**.",
                color=discord.Color.gold()
            )
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            embed = self.build_embed()
            await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="🛑 Dằn Bài (Stand)", style=discord.ButtonStyle.danger)
    async def stand(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.finished:
            return
        self.finished = True
        for child in self.children:
            child.disabled = True

        p_val = calculate_hand(self.player_hand)

        while calculate_hand(self.dealer_hand) < 17 and len(self.dealer_hand) < 5:
            self.dealer_hand.append(draw_card())

        d_val = calculate_hand(self.dealer_hand)

        if d_val > 21:
            self.cog.add_money(interaction.guild_id, self.user.id, self.bet)
            new_bal = self.cog.get_balance(interaction.guild_id, self.user.id)
            outcome = f"🎉 **NHÀ CÁI ĐÃ BỊ QUẮC ({d_val} điểm)!**\n🏆 Bạn thắng nhận **+{self.bet:,} {COIN_SYM}**! Số dư: **{new_bal:,} {COIN_SYM}**."
            color = discord.Color.green()
        elif p_val > d_val:
            self.cog.add_money(interaction.guild_id, self.user.id, self.bet)
            new_bal = self.cog.get_balance(interaction.guild_id, self.user.id)
            outcome = f"🎉 **BẠN ĐÃ CHIẾN THẮNG ({p_val} vs {d_val})!**\n🏆 Bạn nhận **+{self.bet:,} {COIN_SYM}**! Số dư: **{new_bal:,} {COIN_SYM}**."
            color = discord.Color.green()
        elif p_val < d_val:
            self.cog.add_money(interaction.guild_id, self.user.id, -self.bet)
            new_bal = self.cog.get_balance(interaction.guild_id, self.user.id)
            outcome = f"💀 **NHÀ CÁI THẮNG ({d_val} vs {p_val})!**\n💸 Bạn mất **-{self.bet:,} {COIN_SYM}**! Số dư: **{new_bal:,} {COIN_SYM}**."
            color=discord.Color.red()
        else:
            new_bal = self.cog.get_balance(interaction.guild_id, self.user.id)
            outcome = f"🤝 **HÒA ĐIỂM ({p_val} vs {d_val})!**\nBạn được hoàn lại tiền cược **{self.bet:,} {COIN_SYM}**."
            color = discord.Color.yellow()

        embed = self.build_embed(show_dealer=True, outcome=outcome, color=color)
        await interaction.response.edit_message(embed=embed, view=self)


class EconomyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data = load_economy()

    def get_user_data(self, guild_id: int, user_id: int) -> dict:
        g_id = str(guild_id)
        u_id = str(user_id)
        if g_id not in self.data:
            self.data[g_id] = {}
        if u_id not in self.data[g_id]:
            self.data[g_id][u_id] = {
                "wallet": 1000,
                "last_daily": 0,
                "streak": 0,
                "last_work": 0,
                "last_rob": 0,
                "last_beg": 0
            }
            save_economy(self.data)
        return self.data[g_id][u_id]

    def get_balance(self, guild_id: int, user_id: int) -> int:
        return self.get_user_data(guild_id, user_id).get("wallet", 0)

    def set_balance(self, guild_id: int, user_id: int, amount: int):
        u_data = self.get_user_data(guild_id, user_id)
        u_data["wallet"] = max(0, amount)
        save_economy(self.data)

    def add_money(self, guild_id: int, user_id: int, amount: int) -> int:
        u_data = self.get_user_data(guild_id, user_id)
        u_data["wallet"] = max(0, u_data.get("wallet", 0) + amount)
        save_economy(self.data)
        return u_data["wallet"]

    # ================= 1. XEM VÍ TIỀN & CHUYỂN TIỀN =================
    @app_commands.command(name="vi", description="Xem ví tiền NoelCoin (NC) của bạn hoặc người khác")
    async def vi(self, interaction: discord.Interaction, user: Optional[discord.Member] = None):
        target = user or interaction.user
        bal = self.get_balance(interaction.guild_id, target.id)
        u_data = self.get_user_data(interaction.guild_id, target.id)
        streak = u_data.get("streak", 0)

        if bal >= 1000000:
            rank_title = "👑 Trùm Tư Bản / Tỷ Phú Server"
        elif bal >= 500000:
            rank_title = "💎 Đại Gia Khét Tiếng"
        elif bal >= 100000:
            rank_title = "💰 Phú Ông Lớp Học"
        elif bal >= 10000:
            rank_title = "💵 Khá Giả / Có Của Ăn Của Để"
        elif bal >= 1000:
            rank_title = "🍞 Dân Thường Đủ Sống"
        else:
            rank_title = "🌾 Hộ Nghèo Vượt Khó / Ăn Mày"

        embed = discord.Embed(
            title=f"👛 VÍ TIỀN NOELCOIN — {target.display_name}",
            color=discord.Color.gold()
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(name="💰 Số Dư Ví", value=f"**{bal:,} {COIN_SYM}** {COIN_ICON}", inline=True)
        embed.add_field(name="🔥 Chuỗi Điểm Danh", value=f"**{streak} ngày** liên tiếp", inline=True)
        embed.add_field(name="🏷️ Danh Hiệu Tài Phiệt", value=f"`{rank_title}`", inline=False)
        embed.set_footer(text="Dùng /diemdanh, /lam_thue, /an_xin, /taixiu để cày thêm NoelCoin!")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="chuyentien", description="Chuyển tiền NoelCoin (NC) cho một người bạn")
    async def chuyentien(self, interaction: discord.Interaction, nguoi_nhan: discord.Member, so_nc: int):
        if nguoi_nhan.id == interaction.user.id:
            await interaction.response.send_message("❌ Bị khùng hả mà tự chuyển tiền cho mình?", ephemeral=True)
            return

        if nguoi_nhan.bot:
            await interaction.response.send_message("❌ Bot nó không biết tiêu tiền đâu con lợn à!", ephemeral=True)
            return

        if so_nc <= 0:
            await interaction.response.send_message("❌ Số tiền chuyển phải lớn hơn 0 NC!", ephemeral=True)
            return

        sender_bal = self.get_balance(interaction.guild_id, interaction.user.id)
        if sender_bal < so_nc:
            await interaction.response.send_message(f"❌ Bạn không đủ tiền! Số dư hiện tại: **{sender_bal:,} {COIN_SYM}**.", ephemeral=True)
            return

        self.add_money(interaction.guild_id, interaction.user.id, -so_nc)
        self.add_money(interaction.guild_id, nguoi_nhan.id, so_nc)

        embed = discord.Embed(
            title="💸 GIAO DỊCH CHUYỂN TIỀN THÀNH CÔNG",
            description=f"✅ {interaction.user.mention} đã chuyển **{so_nc:,} {COIN_SYM}** cho {nguoi_nhan.mention}!",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)

        await send_log_to_admin(
            interaction.guild,
            title="💸 [KINH TẾ] GIAO DỊCH CHUYỂN TIỀN",
            description=f"{interaction.user.mention} đã chuyển **{so_nc:,} {COIN_SYM}** cho {nguoi_nhan.mention}.",
            color=discord.Color.green()
        )

    # ================= 2. KIẾM TIỀN: ĐIỂM DANH, LÀM THUÊ, ĂN XIN, TRỘM CƯỚP =================
    @app_commands.command(name="an_xin", description="Vác nón rách đi ăn xin kiếm chút tiền lẻ (10 phút/lần)")
    async def an_xin(self, interaction: discord.Interaction):
        u_data = self.get_user_data(interaction.guild_id, interaction.user.id)
        now = time.time()
        last_beg = u_data.get("last_beg", 0)

        # Cooldown 10 phút (600s)
        if now - last_beg < 600:
            remaining = int(600 - (now - last_beg))
            mins = remaining // 60
            secs = remaining % 60
            await interaction.response.send_message(f"⌛ Vừa xin một vòng xong mỏi mồm chưa? Đợi **{mins} phút {secs} giây** nữa hẵng đi vác nón tiếp!", ephemeral=True)
            return

        u_data["last_beg"] = now
        success = random.random() < 0.75  # Tỉ lệ 75% thành công

        if success:
            amount = random.randint(30, 180)
            scenarios = [
                f"Cô bán xôi đầu ngõ thấy {interaction.user.mention} tội nghiệp quá nên ném cho",
                f"Crush đi ngang qua tưởng {interaction.user.mention} bị tâm thần nên bố thí cho",
                f"Bác bảo vệ thương tình dúi vào tay {interaction.user.mention}",
                f"Sếp Ngựa bực mình quăng vào mặt {interaction.user.mention} bảo 'Cầm lấy rồi biến ngay'",
                f"Đi ngang qua quán net thấy người ta bỏ quên",
                f"Một đại gia đi xế hộp hạ kính ném thẳng cọc tiền lẻ",
                f"Thằng bạn thân nhổ bãi nước bọt rồi ném vào nón rách của {interaction.user.mention}"
            ]
            scenario = random.choice(scenarios)
            new_bal = self.add_money(interaction.guild_id, interaction.user.id, amount)

            embed = discord.Embed(
                title="🥺 HÀNH TRÌNH ĂN XIN THÀNH CÔNG! 🌾",
                description=f"🥣 {scenario} **+{amount:,} {COIN_SYM}** {COIN_ICON}!\n"
                            f"💰 Số dư ví hiện tại: **{new_bal:,} {COIN_SYM}**.",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed)
        else:
            fails = [
                f"🤡 {interaction.user.mention} vừa chìa nón ra thì bị chó đuổi cắn rách cả quần chạy té khói!",
                f"👮 Bảo vệ tưởng {interaction.user.mention} là kẻ gian nên cầm chổi quét nhà rượt đánh!",
                f"🤬 Giang hồ đi qua tát cho một phát bảo 'Thanh niên khỏe mạnh không lo đi làm mà ăn xin!'",
                f"💨 Gió thổi một phát bay mất cái nón rách, không xin được một xu nào!",
                f"🚑 Crush đi qua tưởng {interaction.user.mention} bị ngất nên gọi xe cấp cứu 115 đến hốt đi!"
            ]
            fail_msg = random.choice(fails)
            embed = discord.Embed(
                title="💀 ĂN XIN THẤT BẠI CỰC NHỤC! 💨",
                description=fail_msg,
                color=discord.Color.dark_grey()
            )
            await interaction.response.send_message(embed=embed)

    @app_commands.command(name="diemdanh", description="Điểm danh hằng ngày nhận 500 - 1,000 NoelCoin (24h/lần)")
    async def diemdanh(self, interaction: discord.Interaction):
        u_data = self.get_user_data(interaction.guild_id, interaction.user.id)
        now = time.time()
        last_daily = u_data.get("last_daily", 0)
        streak = u_data.get("streak", 0)

        time_diff = now - last_daily
        if time_diff < 86400:
            remaining = int(86400 - time_diff)
            hours = remaining // 3600
            minutes = (remaining % 3600) // 60
            await interaction.response.send_message(f"⏳ Mày đã điểm danh hôm nay rồi! Đợi thêm **{hours} giờ {minutes} phút** nữa nhé.", ephemeral=True)
            return

        if time_diff < 172800:
            streak += 1
        else:
            streak = 1

        base_reward = random.randint(500, 1000)
        bonus = min(streak * 50, 500)
        total_reward = base_reward + bonus

        u_data["last_daily"] = now
        u_data["streak"] = streak
        new_bal = self.add_money(interaction.guild_id, interaction.user.id, total_reward)

        embed = discord.Embed(
            title="📅 ĐIỂM DANH HẰNG NGÀY THÀNH CÔNG! 🎉",
            description=f"Chúc mừng {interaction.user.mention} đã nhận được **+{total_reward:,} {COIN_SYM}** {COIN_ICON}!\n\n"
                        f"• Thưởng gốc: **{base_reward:,} {COIN_SYM}**\n"
                        f"• Thưởng chuỗi (Streak {streak} ngày): **+{bonus:,} {COIN_SYM}**\n"
                        f"• Số dư ví hiện tại: **{new_bal:,} {COIN_SYM}**",
            color=discord.Color.gold()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="lam_thue", description="Đi làm việc vặt trong trường kiếm 100 - 300 NoelCoin (30p/lần)")
    async def lam_thue(self, interaction: discord.Interaction):
        u_data = self.get_user_data(interaction.guild_id, interaction.user.id)
        now = time.time()
        last_work = u_data.get("last_work", 0)

        if now - last_work < 1800:
            remaining = int(1800 - (now - last_work))
            mins = remaining // 60
            secs = remaining % 60
            await interaction.response.send_message(f"😴 Mày vừa làm việc xong mệt muốn đứt hơi! Nghỉ ngơi thêm **{mins} phút {secs} giây** nữa đi.", ephemeral=True)
            return

        jobs = [
            ("Rửa bát căn tin trường học", random.randint(150, 300)),
            ("Trực nhật quét dọn chuồng hề", random.randint(120, 250)),
            ("Bưng nước & đấm lưng cho sếp Ngựa", random.randint(200, 350)),
            ("Chép phạt thuê 100 lần cho bạn bè", random.randint(180, 280)),
            ("Bán trà sữa vỉa hè giờ ra chơi", random.randint(150, 320)),
            ("Lượm ve chai lon nước ngọt sân trường", random.randint(100, 200)),
            ("Lau bảng và cất sổ đầu bài cho cô giáo", random.randint(130, 240)),
            ("Làm lốp dự phòng dắt xe hộ crush", random.randint(160, 290))
        ]

        job_name, wage = random.choice(jobs)
        u_data["last_work"] = now
        new_bal = self.add_money(interaction.guild_id, interaction.user.id, wage)

        embed = discord.Embed(
            title="💼 ĐI LÀM THÊM CHĂM CHỈ",
            description=f"👨‍🌾 {interaction.user.mention} vừa làm công việc: **{job_name}**.\n"
                        f"💵 Tiền công nhận được: **+{wage:,} {COIN_SYM}** {COIN_ICON}\n"
                        f"💰 Số dư ví hiện tại: **{new_bal:,} {COIN_SYM}**",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="cuop", description="Trộm ví tiền của một đứa nào đó (Tỉ lệ 50/50, Cooldown 1h)")
    async def cuop(self, interaction: discord.Interaction, con_moi: discord.Member):
        if con_moi.id == interaction.user.id:
            await interaction.response.send_message("❌ Tự thò tay móc túi mình à thằng ngáo?", ephemeral=True)
            return

        if con_moi.bot:
            await interaction.response.send_message("❌ Đi cướp tiền của Bot là bị cảnh sát tóm đấy!", ephemeral=True)
            return

        u_data = self.get_user_data(interaction.guild_id, interaction.user.id)
        now = time.time()
        last_rob = u_data.get("last_rob", 0)

        if now - last_rob < 3600:
            remaining = int(3600 - (now - last_rob))
            mins = remaining // 60
            await interaction.response.send_message(f"🚔 Cảnh sát đang tuần tra! Đợi **{mins} phút** nữa hẵng đi trộm tiếp.", ephemeral=True)
            return

        robber_bal = self.get_balance(interaction.guild_id, interaction.user.id)
        if robber_bal < 300:
            await interaction.response.send_message(f"❌ Mày quá nghèo (cần ít nhất 300 {COIN_SYM} để làm tiền nộp phạt nếu bị bắt)!", ephemeral=True)
            return

        victim_bal = self.get_balance(interaction.guild_id, con_moi.id)
        if victim_bal < 300:
            await interaction.response.send_message(f"❌ Con mồi {con_moi.mention} nghèo rớt mồng tơi (dưới 300 {COIN_SYM}), tha cho nó đi!", ephemeral=True)
            return

        u_data["last_rob"] = now
        success = random.random() < 0.5

        if success:
            steal_pct = random.uniform(0.10, 0.25)
            stolen = max(100, int(victim_bal * steal_pct))
            self.add_money(interaction.guild_id, con_moi.id, -stolen)
            new_bal = self.add_money(interaction.guild_id, interaction.user.id, stolen)

            embed = discord.Embed(
                title="🥷 VỤ TRỘM THÀNH CÔNG RỰC RỠ! 💰",
                description=f"😈 {interaction.user.mention} đã lẻn vào thó trộm được **+{stolen:,} {COIN_SYM}** từ ví của {con_moi.mention}!\n"
                            f"💰 Số dư của bạn: **{new_bal:,} {COIN_SYM}**.",
                color=discord.Color.green()
            )
            await interaction.response.send_message(content=con_moi.mention, embed=embed)

            await send_log_to_admin(
                interaction.guild,
                title="🥷 [KINH TẾ] TRỘM TIỀN THÀNH CÔNG",
                description=f"{interaction.user.mention} đã trộm **{stolen:,} {COIN_SYM}** từ {con_moi.mention}.",
                color=discord.Color.red()
            )
        else:
            fine = min(robber_bal, random.randint(200, 500))
            self.add_money(interaction.guild_id, interaction.user.id, -fine)
            self.add_money(interaction.guild_id, con_moi.id, fine)
            new_bal = self.get_balance(interaction.guild_id, interaction.user.id)

            embed = discord.Embed(
                title="🚨 BỊ BẮT QUẢ TANG TẠI TRẬN! 🚔",
                description=f"🤡 {interaction.user.mention} thò tay móc túi {con_moi.mention} thì bị vấp ngã ăn đấm!\n"
                            f"💸 Bạn bị phạt đền **-{fine:,} {COIN_SYM}** cho con mồi! Số dư còn: **{new_bal:,} {COIN_SYM}**.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed)

    # ================= 3. SÒNG BẠC MINI: TÀI XỈU, FLIP, XÌ DÁCH =================
    @app_commands.command(name="taixiu", description="Đổ xúc xắc Tài Xỉu (Xỉu: 4-10, Tài: 11-17, Bão: Ăn x3)")
    @app_commands.choices(lua_chon=[
        app_commands.Choice(name="🟢 Xỉu (4 - 10 điểm)", value="xiu"),
        app_commands.Choice(name="🔴 Tài (11 - 17 điểm)", value="tai")
    ])
    async def taixiu(self, interaction: discord.Interaction, tien_cuoc: int, lua_chon: app_commands.Choice[str]):
        if tien_cuoc <= 0:
            await interaction.response.send_message("❌ Tiền cược phải lớn hơn 0 NC!", ephemeral=True)
            return

        bal = self.get_balance(interaction.guild_id, interaction.user.id)
        if bal < tien_cuoc:
            await interaction.response.send_message(f"❌ Bạn không đủ tiền! Số dư hiện tại: **{bal:,} {COIN_SYM}**.", ephemeral=True)
            return

        d1, d2, d3 = random.randint(1, 6), random.randint(1, 6), random.randint(1, 6)
        total = d1 + d2 + d3
        dice_emojis = {1: "⚀", 2: "⚁", 3: "⚂", 4: "⚃", 5: "⚄", 6: "⚅"}
        d_str = f"{dice_emojis[d1]} `{d1}` + {dice_emojis[d2]} `{d2}` + {dice_emojis[d3]} `{d3}` = **{total} điểm**"

        user_choice = lua_chon.value
        is_bao = (d1 == d2 == d3)
        actual_result = "xiu" if total <= 10 else "tai"

        if is_bao:
            if (user_choice == "tai" and total >= 11) or (user_choice == "xiu" and total <= 10):
                win_amt = tien_cuoc * 3
                new_bal = self.add_money(interaction.guild_id, interaction.user.id, win_amt)
                outcome = f"🌪️ **BÃO XÚC XẮC 3 CON {d1}!**\n🎉 Bạn đoán trúng bão nhận thưởng **GẤP 3: +{win_amt:,} {COIN_SYM}**! Số dư: **{new_bal:,} {COIN_SYM}**."
                color = discord.Color.gold()
            else:
                new_bal = self.add_money(interaction.guild_id, interaction.user.id, -tien_cuoc)
                outcome = f"🌪️ **BÃO XÚC XẮC 3 CON {d1}!**\n💀 Nhà cái hốt trọn ổ! Bạn mất **-{tien_cuoc:,} {COIN_SYM}**! Số dư: **{new_bal:,} {COIN_SYM}**."
                color = discord.Color.red()
        elif user_choice == actual_result:
            new_bal = self.add_money(interaction.guild_id, interaction.user.id, tien_cuoc)
            outcome = f"🎉 **BẠN ĐÃ ĐOÁN ĐÚNG ({actual_result.upper()})!**\n🏆 Thắng nhận **+{tien_cuoc:,} {COIN_SYM}**! Số dư: **{new_bal:,} {COIN_SYM}**."
            color = discord.Color.green()
        else:
            new_bal = self.add_money(interaction.guild_id, interaction.user.id, -tien_cuoc)
            outcome = f"💀 **BẠN ĐÃ ĐOÁN SAI ({actual_result.upper()})!**\n💸 Bạn mất **-{tien_cuoc:,} {COIN_SYM}**! Số dư: **{new_bal:,} {COIN_SYM}**."
            color = discord.Color.red()

        embed = discord.Embed(
            title="🎲 SÒNG BẠC TÀI XỈU 🎲",
            description=f"**Người chơi:** {interaction.user.mention} | **Cược:** **{tien_cuoc:,} {COIN_SYM}** vào **{lua_chon.name}**\n\n"
                        f"🎲 **Kết Quả Đổ Xúc Xắc:**\n{d_str}\n\n"
                        f"{outcome}",
            color=color
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="flip", description="Tung đồng xu ăn tiền (Sấp / Ngửa, Ăn 1:1)")
    @app_commands.choices(mat=[
        app_commands.Choice(name="🟡 Ngửa (Heads)", value="ngua"),
        app_commands.Choice(name="⚪ Sấp (Tails)", value="sap")
    ])
    async def flip(self, interaction: discord.Interaction, tien_cuoc: int, mat: app_commands.Choice[str]):
        if tien_cuoc <= 0:
            await interaction.response.send_message("❌ Tiền cược phải lớn hơn 0 NC!", ephemeral=True)
            return

        bal = self.get_balance(interaction.guild_id, interaction.user.id)
        if bal < tien_cuoc:
            await interaction.response.send_message(f"❌ Bạn không đủ tiền! Số dư hiện tại: **{bal:,} {COIN_SYM}**.", ephemeral=True)
            return

        result = random.choice(["ngua", "sap"])
        coin_str = "🟡 **MẶT NGỬA**" if result == "ngua" else "⚪ **MẶT SẤP**"

        if mat.value == result:
            new_bal = self.add_money(interaction.guild_id, interaction.user.id, tien_cuoc)
            outcome = f"🎉 **BẠN ĐÃ ĐOÁN ĐÚNG!**\n🏆 Thắng nhận **+{tien_cuoc:,} {COIN_SYM}**! Số dư: **{new_bal:,} {COIN_SYM}**."
            color = discord.Color.green()
        else:
            new_bal = self.add_money(interaction.guild_id, interaction.user.id, -tien_cuoc)
            outcome = f"💀 **BẠN ĐÃ ĐOÁN SAI!**\n💸 Mất trắng **-{tien_cuoc:,} {COIN_SYM}**! Số dư: **{new_bal:,} {COIN_SYM}**."
            color = discord.Color.red()

        embed = discord.Embed(
            title="🪙 TUNG ĐỒNG XU MAY RỦI 🪙",
            description=f"**Người chơi:** {interaction.user.mention} | **Cược:** **{tien_cuoc:,} {COIN_SYM}** vào **{mat.name}**\n\n"
                        f"🪙 **Kết quả rơi xuống:** {coin_str}\n\n"
                        f"{outcome}",
            color=color
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="xidach", description="Đánh bài Xì Dách (Blackjack 21 điểm) với Bot bằng nút bấm")
    async def xidach(self, interaction: discord.Interaction, tien_cuoc: int):
        if tien_cuoc <= 0:
            await interaction.response.send_message("❌ Tiền cược phải lớn hơn 0 NC!", ephemeral=True)
            return

        bal = self.get_balance(interaction.guild_id, interaction.user.id)
        if bal < tien_cuoc:
            await interaction.response.send_message(f"❌ Bạn không đủ tiền! Số dư hiện tại: **{bal:,} {COIN_SYM}**.", ephemeral=True)
            return

        player_hand = [draw_card(), draw_card()]
        dealer_hand = [draw_card(), draw_card()]

        p_val = calculate_hand(player_hand)
        
        if p_val == 21:
            win_amt = int(tien_cuoc * 1.5)
            self.add_money(interaction.guild_id, interaction.user.id, win_amt)
            new_bal = self.get_balance(interaction.guild_id, interaction.user.id)

            p_cards = " ".join(card_to_str(c) for c in player_hand)
            d_cards = " ".join(card_to_str(c) for c in dealer_hand)

            embed = discord.Embed(
                title="🃏 XÌ DÁCH TỰ NHIÊN (BLACKJACK)! 🌟",
                description=f"**Người chơi:** {interaction.user.mention} | **Cược:** **{tien_cuoc:,} {COIN_SYM}**\n\n"
                            f"**Bài Của Bạn:** {p_cards} `(21 ĐIỂM XÌ DÁCH)`\n"
                            f"**Bài Nhà Cái:** {d_cards}\n\n"
                            f"🏆 **BẠN THẮNG LỚN ĂN GẤP RƯỠI:** **+{win_amt:,} {COIN_SYM}**! Số dư: **{new_bal:,} {COIN_SYM}**.",
                color=discord.Color.gold()
            )
            await interaction.response.send_message(embed=embed)
            return

        view = BlackjackView(self, interaction.user, tien_cuoc, player_hand, dealer_hand)
        embed = view.build_embed()
        await interaction.response.send_message(embed=embed, view=view)

    # ================= 4. BẢNG XẾP HẠNG ĐẠI GIA =================
    @app_commands.command(name="top_dai_gia", description="Bảng xếp hạng Top 10 đại gia sở hữu nhiều NoelCoin nhất")
    async def top_dai_gia(self, interaction: discord.Interaction):
        g_id = str(interaction.guild_id)
        guild_data = self.data.get(g_id, {})

        if not guild_data:
            await interaction.response.send_message("Chưa có dữ liệu kinh tế nào trong Server.", ephemeral=True)
            return

        sorted_users = sorted(guild_data.items(), key=lambda x: x[1].get("wallet", 0), reverse=True)

        embed = discord.Embed(
            title="🏆 BẢNG PHONG THẦN ĐẠI GIA (TOP 10 NOELCOIN) 🌟",
            description="Vinh danh những gương mặt tài phiệt nắm giữ nền kinh tế của Server:\n",
            color=discord.Color.gold()
        )

        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        desc = ""
        for i, (u_id, data) in enumerate(sorted_users[:10]):
            bal = data.get("wallet", 0)
            medal = medals[i] if i < len(medals) else f"#{i+1}"
            desc += f"{medal} <@{u_id}> — **{bal:,} {COIN_SYM}** {COIN_ICON}\n"

        embed.description = desc
        embed.set_footer(text="Dùng /vi để kiểm tra số dư ví của chính bạn!")
        await interaction.response.send_message(embed=embed)

    # ================= 5. QUYỀN HẠN ADMIN (SET, ADD, TRỪ TIỀN, RESET) =================
    @app_commands.command(name="set_nc", description="Admin đặt thẳng số dư NoelCoin cho một thành viên (Admin)")
    @app_commands.default_permissions(administrator=True)
    async def set_nc(self, interaction: discord.Interaction, user: discord.Member, so_tien: int):
        user_perms = interaction.user.guild_permissions
        if not (user_perms.administrator or user_perms.manage_guild):
            await interaction.response.send_message("❌ Mày phải có quyền Admin mới được dùng lệnh này!", ephemeral=True)
            return

        self.set_balance(interaction.guild_id, user.id, so_tien)
        await interaction.response.send_message(f"👑 Admin {interaction.user.mention} đã đặt số dư của {user.mention} thành **{so_tien:,} {COIN_SYM}** {COIN_ICON}!")

        await send_log_to_admin(
            interaction.guild,
            title="👑 [ADMIN] THIẾT LẬP SỐ DƯ NOELCOIN",
            description=f"Admin {interaction.user.mention} đã đặt ví của {user.mention} thành **{so_tien:,} {COIN_SYM}**.",
            color=discord.Color.gold()
        )

    @app_commands.command(name="add_nc", description="Admin cộng thêm NoelCoin cho một thành viên (Admin)")
    @app_commands.default_permissions(administrator=True)
    async def add_nc(self, interaction: discord.Interaction, user: discord.Member, so_tien: int):
        user_perms = interaction.user.guild_permissions
        if not (user_perms.administrator or user_perms.manage_guild):
            await interaction.response.send_message("❌ Mày phải có quyền Admin mới được dùng lệnh này!", ephemeral=True)
            return

        new_bal = self.add_money(interaction.guild_id, user.id, so_tien)
        await interaction.response.send_message(f"✨ Admin {interaction.user.mention} đã cộng **+{so_tien:,} {COIN_SYM}** cho {user.mention} (Tổng ví: **{new_bal:,} {COIN_SYM}**)!")

        await send_log_to_admin(
            interaction.guild,
            title="✨ [ADMIN] CỘNG THƯỞNG NOELCOIN",
            description=f"Admin {interaction.user.mention} đã cộng **+{so_tien:,} {COIN_SYM}** cho {user.mention}.",
            color=discord.Color.green()
        )

    @app_commands.command(name="tru_nc", description="Admin trừ / phạt một số NoelCoin xác định của một thành viên (Admin)")
    @app_commands.default_permissions(administrator=True)
    async def tru_nc(self, interaction: discord.Interaction, user: discord.Member, so_tien: int, ly_do: Optional[str] = "Bị phạt"):
        user_perms = interaction.user.guild_permissions
        if not (user_perms.administrator or user_perms.manage_guild):
            await interaction.response.send_message("❌ Mày phải có quyền Admin mới được dùng lệnh này!", ephemeral=True)
            return

        new_bal = self.add_money(interaction.guild_id, user.id, -so_tien)
        await interaction.response.send_message(f"⚠️ Admin {interaction.user.mention} đã **phạt trừ -{so_tien:,} {COIN_SYM}** của {user.mention} (Lý do: *{ly_do}*). Số dư còn: **{new_bal:,} {COIN_SYM}**!")

        await send_log_to_admin(
            interaction.guild,
            title="⚠️ [ADMIN] PHẠT TRỪ NOELCOIN",
            description=f"Admin {interaction.user.mention} đã phạt trừ **-{so_tien:,} {COIN_SYM}** của {user.mention}.\nLý do: *{ly_do}*",
            color=discord.Color.red()
        )

    @app_commands.command(name="reset_all_nc", description="Admin xóa sạch toàn bộ tiền NoelCoin của Server về mặc định (Admin)")
    @app_commands.default_permissions(administrator=True)
    async def reset_all_nc(self, interaction: discord.Interaction):
        user_perms = interaction.user.guild_permissions
        if not (user_perms.administrator or user_perms.manage_guild):
            await interaction.response.send_message("❌ Mày phải có quyền Admin mới được dùng lệnh này!", ephemeral=True)
            return

        save_economy({})
        self.data = {}
        await interaction.response.send_message(f"🧹 Admin {interaction.user.mention} đã reset toàn bộ nền kinh tế Server về 0! Tất cả mọi người trở lại làm dân nghèo!")

        await send_log_to_admin(
            interaction.guild,
            title="🧹 [ADMIN] RESET TOÀN BỘ TIỀN TỆ NOELCOIN",
            description=f"Admin {interaction.user.mention} đã xóa sạch dữ liệu tiền tệ của Server.",
            color=discord.Color.red()
        )

    # ================= LỆNH NHANH DẤU CHẤM THAN (!) CHO ADMIN & MEMBER =================
    @commands.command(name="buffnc")
    @commands.has_permissions(administrator=True)
    async def cmd_buffnc(self, ctx, so_tien: int = 1000000):
        """!buffnc 1000000 -> Tự bơm tiền cho chính Admin"""
        new_bal = self.add_money(ctx.guild.id, ctx.author.id, so_tien)
        await ctx.send(f"🚀 **BUFF THÀNH CÔNG!** Admin {ctx.author.mention} vừa tự bơm **+{so_tien:,} {COIN_SYM}** {COIN_ICON} (Số dư ví: **{new_bal:,} {COIN_SYM}**)! 🤑👑")

    @commands.command(name="setnc")
    @commands.has_permissions(administrator=True)
    async def cmd_setnc(self, ctx, user: discord.Member, so_tien: int):
        """!setnc @user 50000"""
        self.set_balance(ctx.guild.id, user.id, so_tien)
        await ctx.send(f"👑 Đã đặt số dư của {user.mention} thành **{so_tien:,} {COIN_SYM}**!")

    @commands.command(name="addnc")
    @commands.has_permissions(administrator=True)
    async def cmd_addnc(self, ctx, user: discord.Member, so_tien: int):
        """!addnc @user 10000"""
        new_bal = self.add_money(ctx.guild.id, user.id, so_tien)
        await ctx.send(f"✨ Đã cộng **+{so_tien:,} {COIN_SYM}** cho {user.mention} (Tổng ví: **{new_bal:,} {COIN_SYM}**)! 💰")

    @commands.command(name="trunc")
    @commands.has_permissions(administrator=True)
    async def cmd_trunc(self, ctx, user: discord.Member, so_tien: int):
        """!trunc @user 5000 -> Phạt trừ tiền"""
        new_bal = self.add_money(ctx.guild.id, user.id, -so_tien)
        await ctx.send(f"⚠️ Đã phạt trừ **-{so_tien:,} {COIN_SYM}** của {user.mention}! Số dư còn: **{new_bal:,} {COIN_SYM}**!")

    @commands.command(name="vi")
    async def cmd_vi(self, ctx, user: Optional[discord.Member] = None):
        """!vi hoặc !vi @user"""
        target = user or ctx.author
        bal = self.get_balance(ctx.guild.id, target.id)
        await ctx.send(f"👛 Ví của {target.mention}: **{bal:,} {COIN_SYM}** {COIN_ICON}")

    @commands.command(name="anxin")
    async def cmd_anxin(self, ctx):
        """!anxin -> Ăn xin nhanh"""
        u_data = self.get_user_data(ctx.guild.id, ctx.author.id)
        now = time.time()
        last_beg = u_data.get("last_beg", 0)

        if now - last_beg < 600:
            remaining = int(600 - (now - last_beg))
            mins = remaining // 60
            secs = remaining % 60
            await ctx.send(f"⌛ Vừa xin một vòng xong mỏi mồm chưa? Đợi **{mins} phút {secs} giây** nữa nhé {ctx.author.mention}!")
            return

        u_data["last_beg"] = now
        success = random.random() < 0.75
        if success:
            amt = random.randint(30, 180)
            new_bal = self.add_money(ctx.guild.id, ctx.author.id, amt)
            await ctx.send(f"🥺 {ctx.author.mention} vừa vác nón rách đi xin được **+{amt:,} {COIN_SYM}** {COIN_ICON}! (Ví: **{new_bal:,} {COIN_SYM}**)")
        else:
            await ctx.send(f"💀 {ctx.author.mention} vừa chìa nón ra xin thì bị bảo vệ cầm chổi rượt đánh chạy té khói!")


async def setup(bot):
    await bot.add_cog(EconomyCog(bot))
