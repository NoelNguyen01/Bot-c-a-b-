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
                if file.stem not in ["__init__", "quotes_data", "admin_log"]:
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

    async def purge_and_sync_commands(self, guild: discord.Guild = None):
        """Hàm dọn dẹp triệt để mọi lệnh rác cũ trên Discord API"""
        logger.info("Bắt đầu quy trình dọn dẹp triệt để lệnh Discord...")
        
        # 1. Lấy danh sách tên lệnh hợp lệ hiện tại trong code
        valid_command_names = {cmd.name for cmd in self.tree.get_commands()}
        logger.info(f"Các lệnh hợp lệ hiện tại ({len(valid_command_names)}): {valid_command_names}")

        # 2. Xóa sạch mọi lệnh thừa ở từng Guild
        target_guilds = [guild] if guild else self.guilds
        for g in target_guilds:
            try:
                # Xóa sạch guild commands
                self.tree.clear_commands(guild=g)
                await self.tree.sync(guild=g)
                logger.info(f"🧹 Đã xóa sạch guild commands cho {g.name}")
            except Exception as e:
                logger.warning(f"Lỗi clear guild commands {g.name}: {e}")

        # 3. Đồng bộ lại Global tree chuẩn xác 100%
        try:
            synced_global = await self.tree.sync()
            logger.info(f"⚡ Đã đồng bộ Global thành công ({len(synced_global)} lệnh): {[c.name for c in synced_global]}")
            return synced_global
        except Exception as e:
            logger.error(f"Lỗi sync global: {e}")
            raise e

    async def on_ready(self) -> None:
        logger.info(f"Bot đã đăng nhập thành công: {self.user} (ID: {self.user.id})")
        try:
            await self.change_presence(
                status=discord.Status.online,
                activity=discord.Game(name="/hdsd | Chúa Tể Cà Khịa 🤡")
            )
        except Exception:
            pass

        try:
            await self.purge_and_sync_commands()
        except Exception as e:
            logger.error(f"Lỗi tự động purge khi on_ready: {e}")

        logger.info(f"Đang kết nối tới {len(self.guilds)} máy chủ Discord.")
        print("\n" + "="*50)
        print("       🤡 BOT ĐÃ SẴN SÀNG QUẬY PHÁ! 🤡       ")
        print("="*50 + "\n")


bot = TrollBot()

@bot.command(name="sync")
@commands.has_permissions(administrator=True)
async def manual_sync(ctx):
    """Lệnh !sync cho Admin để xóa tận gốc mọi lệnh cũ trên Discord"""
    async with ctx.typing():
        try:
            synced = await bot.purge_and_sync_commands(guild=ctx.guild)
            cmd_list = ", ".join([f"`/{c.name}`" for c in synced])
            await ctx.send(
                f"🧹 **ĐÃ XÓA SẠCH 100% LỆNH RÁC & CỜ BẠC CŨ TRÊN DISCORD!** 🎉\n\n"
                f"📋 **Danh sách chuẩn hiện tại ({len(synced)} lệnh):**\n{cmd_list}\n\n"
                f"👉 *Nếu Discord chưa cập nhật ngay, bạn hãy bấm **Ctrl + R** (hoặc khởi động lại app Discord) để xóa cache nhé!*"
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
