# -*- coding: utf-8 -*-
import asyncio
import logging
import os
import sys
from pathlib import Path

import aiohttp.web
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("TrollBot")

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")


async def start_keep_alive_web():
    port = int(os.getenv("PORT", 8080))
    app = aiohttp.web.Application()
    app.router.add_get("/", lambda r: aiohttp.web.Response(text="Bot đang hoạt động 24/7!"))
    runner = aiohttp.web.AppRunner(app)
    await runner.setup()
    site = aiohttp.web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"🌐 Web keep-alive server đang chạy trên cổng {port}")


class TrollBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        intents.voice_states = True

        super().__init__(
            command_prefix=commands.when_mentioned_or("!"),
            intents=intents,
            help_command=None,
            status=discord.Status.online,
            activity=discord.Game(name="/hdsd | Chúa Tể Cà Khịa 🤡"),
        )

    async def setup_hook(self) -> None:
        if os.getenv("PORT") or os.getenv("RENDER"):
            asyncio.create_task(start_keep_alive_web())

        cogs_dir = Path(__file__).parent / "cogs"
        if cogs_dir.exists() and cogs_dir.is_dir():
            for file in cogs_dir.glob("*.py"):
                if file.stem not in ["__init__", "quotes_data"]:
                    cog_name = f"cogs.{file.stem}"
                    try:
                        await self.load_extension(cog_name)
                        logger.info(f"Đã tải thành công Cog: {cog_name}")
                    except Exception as e:
                        logger.error(f"Lỗi khi nạp Cog {cog_name}: {e}", exc_info=True)

        self.tree.on_error = self.on_tree_error

    async def on_tree_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ) -> None:
        if isinstance(error, app_commands.CommandOnCooldown):
            retry_after = error.retry_after
            msg = f"⏳ Từ từ thôi con lợn, spam lắm Discord nó khóa mồm tao bây giờ! Đợi **{retry_after:.0f} giây** nữa đi."
            if interaction.response.is_done():
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.response.send_message(msg, ephemeral=True)
            return

        if isinstance(error, app_commands.MissingPermissions):
            msg = "❌ Mày không có quyền Quản trị viên (Admin) để dùng lệnh này nha!"
            if interaction.response.is_done():
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.response.send_message(msg, ephemeral=True)
            return

        command_name = interaction.command.name if interaction.command else "Không rõ"
        logger.error(f"Lỗi lệnh /{command_name}: {error}", exc_info=True)
        error_msg = f"Có lỗi xảy ra: {error}"
        if interaction.response.is_done():
            await interaction.followup.send(error_msg, ephemeral=True)
        else:
            await interaction.response.send_message(error_msg, ephemeral=True)

    async def deep_clean_commands(self) -> list:
        """Xóa vĩnh viễn từng lệnh rác trực tiếp từ máy chủ Discord"""
        logger.info("Bắt đầu truy quét và xóa từng lệnh rác...")
        app_id = self.application_id or self.user.id
        current_valid_names = {cmd.name for cmd in self.tree.get_commands()}
        deleted_cmds = []

        # 1. Quét và xóa các Global Commands không còn trong code
        try:
            global_cmds = await self.tree.fetch_commands()
            for cmd in global_cmds:
                if cmd.name not in current_valid_names:
                    try:
                        await self.http.delete_global_command(app_id, cmd.id)
                        logger.info(f"🔥 ĐÃ XÓA TRỰC TIẾP LỆNH GLOBAL RÁC: /{cmd.name} (ID: {cmd.id})")
                        deleted_cmds.append(f"`/{cmd.name}`")
                    except Exception as e:
                        logger.error(f"Lỗi xóa lệnh /{cmd.name}: {e}")
        except Exception as e:
            logger.error(f"Lỗi fetch global commands: {e}")

        # 2. Quét và xóa các Guild Commands ở từng Server
        for g in self.guilds:
            try:
                guild_cmds = await self.tree.fetch_commands(guild=g)
                for cmd in guild_cmds:
                    if cmd.name not in current_valid_names:
                        try:
                            await self.http.delete_guild_command(app_id, g.id, cmd.id)
                            logger.info(f"🔥 ĐÃ XÓA LỆNH GUILD RÁC: /{cmd.name} ở Server {g.name}")
                            deleted_cmds.append(f"`/{cmd.name}` (ở {g.name})")
                        except Exception as e:
                            logger.error(f"Lỗi xóa guild cmd /{cmd.name}: {e}")
            except Exception as e:
                logger.error(f"Lỗi fetch guild commands {g.name}: {e}")

        # 3. Đồng bộ lại danh sách chuẩn sạch sẽ
        try:
            await self.tree.sync()
        except Exception as e:
            logger.error(f"Lỗi sync: {e}")

        return deleted_cmds

    async def on_ready(self) -> None:
        logger.info(f"Bot đã đăng nhập thành công: {self.user} (ID: {self.user.id})")
        try:
            await self.change_presence(
                status=discord.Status.online,
                activity=discord.Game(name="/hdsd | Chúa Tể Cà Khịa 🤡")
            )
        except Exception:
            pass

        # Tự động dọn sạch rác ngay khi khởi động
        try:
            deleted = await self.deep_clean_commands()
            if deleted:
                logger.info(f"Đã tự động xóa sạch các lệnh rác: {', '.join(deleted)}")
            else:
                logger.info("Không có lệnh rác nào cần xóa.")
        except Exception as e:
            logger.error(f"Lỗi dọn rác on_ready: {e}")

        logger.info(f"Đang kết nối tới {len(self.guilds)} máy chủ Discord.")
        print("\n" + "="*50)
        print("       🤡 BOT ĐÃ SẴN SÀNG QUẬY PHÁ! 🤡       ")
        print("="*50 + "\n")


bot = TrollBot()

@bot.command(name="sync")
@commands.has_permissions(administrator=True)
async def manual_sync(ctx):
    """Lệnh !sync cho Admin để ép xóa vĩnh viễn mọi lệnh rác từ Discord API"""
    async with ctx.typing():
        try:
            deleted = await bot.deep_clean_commands()
            valid_cmds = [f"`/{c.name}`" for c in bot.tree.get_commands()]
            
            del_msg = f"🔥 **Đã xóa vĩnh viễn các lệnh cờ bạc/rác:** {', '.join(deleted)}\n\n" if deleted else "✨ **Không còn lệnh rác nào trên Discord!**\n\n"
            await ctx.send(
                f"🧹 **KẾT QUẢ DỌN DẸP DISCORD:**\n"
                f"{del_msg}"
                f"📋 **Danh sách lệnh chuẩn ({len(valid_cmds)} lệnh):**\n{', '.join(valid_cmds)}\n\n"
                f"👉 *Nhấn **Ctrl + R** trên Discord để làm mới bảng gợi ý!*"
            )
        except Exception as e:
            await ctx.send(f"❌ Lỗi khi sync: `{e}`")


async def main() -> None:
    if not TOKEN:
        logger.critical("Không tìm thấy DISCORD_TOKEN trong file .env!")
        sys.exit(1)

    async with bot:
        await bot.start(TOKEN)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot đã được dừng thủ công bởi người dùng.")
