import asyncio
import logging
import os
import sys
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

# Thiết lập logging cho bot
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("ClassTrollBot")

# Nạp các biến môi trường từ tệp .env
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")


class TrollBot(commands.Bot):
    """Lớp Bot chính kế thừa từ commands.Bot của discord.py 2.x"""

    def __init__(self) -> None:
        # Bật toàn bộ Intents bao gồm members, message_content, voice_states
        intents = discord.Intents.all()
        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None,
        )

    async def setup_hook(self) -> None:
        """Tự động tải tất cả các cogs trong thư mục cogs/ và thiết lập error handler cho Slash Commands"""
        cogs_dir = Path(__file__).parent / "cogs"
        if cogs_dir.exists() and cogs_dir.is_dir():
            for file in cogs_dir.glob("*.py"):
                if file.stem != "__init__":
                    cog_name = f"cogs.{file.stem}"
                    try:
                        await self.load_extension(cog_name)
                        logger.info(f"Đã tải thành công Cog: {cog_name}")
                    except Exception as e:
                        logger.error(f"Lỗi khi nạp Cog {cog_name}: {e}", exc_info=True)

        # Đăng ký xử lý lỗi toàn cục cho app_commands (Slash Commands)
        self.tree.on_error = self.on_tree_error

    async def on_tree_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ) -> None:
        """Xử lý lỗi toàn cục cho các Slash Commands"""
        # Xử lý khi bị cooldown
        if isinstance(error, app_commands.CommandOnCooldown):
            retry_after = error.retry_after
            msg = f"Từ từ thôi con lợn, spam lắm Discord nó khóa mồm tao bây giờ! Đợi {retry_after:.0f} giây nữa đi."
            if interaction.response.is_done():
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.response.send_message(msg, ephemeral=True)
            return

        # Xử lý các lỗi khác
        command_name = interaction.command.name if interaction.command else "Không rõ"
        logger.error(f"Lỗi khi thực thi lệnh /{command_name}: {error}", exc_info=True)
        error_msg = "Có lỗi xảy ra khi thực hiện lệnh rồi con lợn ơi!"
        if interaction.response.is_done():
            await interaction.followup.send(error_msg, ephemeral=True)
        else:
            await interaction.response.send_message(error_msg, ephemeral=True)

    async def on_ready(self) -> None:
        """Sự kiện kích hoạt khi bot sẵn sàng hoạt động"""
        logger.info(f"Bot đã đăng nhập thành công: {self.user} (ID: {self.user.id})")

        # Đồng bộ Slash Commands với Discord API
        try:
            synced = await self.tree.sync()
            logger.info(f"Đã đồng bộ thành công {len(synced)} Slash Commands.")
        except Exception as e:
            logger.error(f"Lỗi khi đồng bộ Slash Commands: {e}", exc_info=True)

        logger.info(f"Đang kết nối tới {len(self.guilds)} máy chủ Discord.")
        logger.info("==========================================")
        logger.info("       BOT ĐÃ SẴN SÀNG QUẬY PHÁ!          ")
        logger.info("==========================================")


async def main() -> None:
    if not TOKEN:
        logger.critical("Không tìm thấy DISCORD_TOKEN trong file .env! Vui lòng cấu hình token trước khi khởi chạy.")
        sys.exit(1)

    bot = TrollBot()
    async with bot:
        await bot.start(TOKEN)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot đã được dừng thủ công bởi người dùng.")
