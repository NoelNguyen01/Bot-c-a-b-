import discord
from discord.ext import commands
import random

class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.join_messages = [
            "Chào mừng con mồi mới {tag} đã gia nhập chuồng hề. 🤡",
            "Ơ kìa {tag} lạc vào chuồng thú rồi à? Chào mừng nhé! 🎪",
            "Thêm một nạn nhân mới... à nhầm, thêm một thành viên mới {tag}! Chào mừng! 🎉"
        ]
        self.leave_messages = [
            "Tiễn vong {name}, không chịu nổi nhiệt đã bấm nút biến. 💨",
            "{name} đã sủi rồi nhé cả nhà, F trong chat. ⚰️",
            "Một con chim đã rời đàn... {name} bay đi không một lời từ biệt. 🕊️"
        ]
        self.vc_join_messages = [
            "Chào mừng đại ca {mention} đã mò mặt vào chuồng. 🎙️",
            "{mention} đã xuất hiện! Huyền thoại trở lại! 👑",
            "Ơ kìa {mention} hôm nay cũng rảnh à? 😏"
        ]
        self.vc_leave_messages = [
            "{mention} lại sủi đi ỉa rồi à? 💩",
            "{mention} đã cúp đuôi chạy trốn. 🏃",
            "{mention} biến mất nhanh hơn crush rep tin nhắn mày. 💨"
        ]

    @commands.Cog.listener()
    async def on_member_join(self, member):
        channel = member.guild.system_channel
        if channel:
            msg = random.choice(self.join_messages).format(tag=member.mention)
            await channel.send(msg)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        channel = member.guild.system_channel
        if channel:
            msg = random.choice(self.leave_messages).format(name=member.display_name)
            await channel.send(msg)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        # Join Voice
        if before.channel is None and after.channel is not None:
            msg = random.choice(self.vc_join_messages).format(mention=member.mention)
            try:
                await after.channel.send(msg)
            except discord.Forbidden:
                pass
            except AttributeError:
                pass

        # Leave Voice
        elif before.channel is not None and after.channel is None:
            msg = random.choice(self.vc_leave_messages).format(mention=member.mention)
            try:
                await before.channel.send(msg)
            except discord.Forbidden:
                pass
            except AttributeError:
                pass

async def setup(bot):
    await bot.add_cog(Welcome(bot))
