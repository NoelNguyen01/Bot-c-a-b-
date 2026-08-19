# -*- coding: utf-8 -*-
import discord
from discord.ext import commands
from discord import app_commands
import edge_tts
import asyncio
import tempfile
import os
import re
import logging
import imageio_ffmpeg

logger = logging.getLogger("VoiceTTS")

# SIÊU BỘ TỪ ĐIỂN DỊCH VIẾT TẮT, TEENCODE & NÓI LÁI TỪ TỤC (180+ TỪ)
VIETNAMESE_ABBREVIATIONS = [
    # 1. Cụm từ chửi thề nói lái tấu hài (ưu tiên cụm dài trước)
    (r'\bđcmm\b', 'đậu cả nhà mày'),
    (r'\bdcmm\b', 'đậu cả nhà mày'),
    (r'\bđcmn\b', 'đậu cả mâm này'),
    (r'\bdcmn\b', 'đậu cả mâm này'),
    (r'\bclgt\b', 'cái lề gì thốn'),
    (r'\bvcl\b', 'vãi cả lúa'),
    (r'\bvkl\b', 'vãi cả lúa'),
    (r'\bvch\b', 'vãi chưởng'),
    (r'\bvcc\b', 'vãi cà chua'),
    (r'\bvcb\b', 'vãi cả bưởi'),
    (r'\bvcd\b', 'vãi cả dừa'),
    (r'\bcmnr\b', 'chuẩn mẹ nó rồi'),
    (r'\bcmn\b', 'chuẩn mẹ nó'),
    (r'\bdcm\b', 'đậu cả mâm'),
    (r'\bđcm\b', 'đậu cả mâm'),
    (r'\bdmm\b', 'đậu mè mày'),
    (r'\bđmm\b', 'đậu mè mày'),
    (r'\bdm\b', 'đậu má'),
    (r'\bđm\b', 'đậu má'),
    (r'\bđịt mẹ mày\b', 'đậu má mày'),
    (r'\bdit me may\b', 'đậu má mày'),
    (r'\bđịt mẹ\b', 'đậu má'),
    (r'\bdit me\b', 'đậu má'),
    (r'\bvl\b', 'vãi lúa'),
    (r'\bvđ\b', 'vãi đạn'),
    (r'\bvd\b', 'vãi đạn'),
    (r'\bcl\b', 'cái lề'),
    (r'\bcc\b', 'cục cứt'),
    (r'\bcon cc\b', 'con cào cào'),
    (r'\bloz\b', 'lầu'),
    (r'\blon\b', 'lầu'),
    (r'\blồn\b', 'lầu'),
    (r'\bbuoi\b', 'bưởi'),
    (r'\bbuồi\b', 'bưởi'),
    (r'\bcặc\b', 'củ cải'),
    (r'\bcac\b', 'củ cải'),
    (r'\bđịt\b', 'đậu'),
    (r'\bdit\b', 'đậu'),
    (r'\bchó chết\b', 'chó cắn'),
    (r'\bóc chó\b', 'óc quả nho'),
    (r'\boc cho\b', 'óc quả nho'),
    (r'\bxlon\b', 'xạo lầu'),
    (r'\bxl\b', 'xạo lầu'),
    (r'\bvlxx\b', 'phim con heo'),

    # 2. Hoạt động & Trạng thái hàng ngày
    (r'\bđg\b', 'đang'),
    (r'\bdg\b', 'đang'),
    (r'\bđx\b', 'được'),
    (r'\bdx\b', 'được'),
    (r'\bdc\b', 'được'),
    (r'\bđc\b', 'được'),
    (r'\bđk\b', 'được'),
    (r'\bdk\b', 'được'),
    (r'\bdcch\b', 'được chưa'),
    (r'\brchx\b', 'rồi chưa'),
    (r'\br\b', 'rồi'),
    (r'\broi\b', 'rồi'),
    (r'\brùi\b', 'rồi'),
    (r'\bchx\b', 'chưa'),
    (r'\bchua\b', 'chưa'),
    (r'\bđr\b', 'đúng rồi'),
    (r'\bdr\b', 'đúng rồi'),
    (r'\bđbh\b', 'đời nào'),
    (r'\bxđ\b', 'xác định'),
    (r'\bxd\b', 'xác định'),
    (r'\bsnghi\b', 'suy nghĩ'),
    (r'\btl\b', 'trả lời'),
    (r'\brep\b', 'trả lời'),
    (r'\bseen\b', 'đã xem'),
    (r'\bhqua\b', 'hôm qua'),
    (r'\bhnay\b', 'hôm nay'),
    (r'\bhnie\b', 'hôm nay'),
    (r'\bngmai\b', 'ngày mai'),
    (r'\bmmai\b', 'ngày mai'),
    (r'\bbjo\b', 'bây giờ'),
    (r'\bbh\b', 'bây giờ'),
    (r'\bh\b', 'giờ'),
    (r'\btrog\b', 'trong'),
    (r'\btrg\b', 'trong'),
    (r'\bngoai\b', 'ngoài'),
    (r'\blms\b', 'làm sao'),
    (r'\blm\b', 'làm'),
    (r'\bnoi\b', 'nói'),
    (r'\bns\b', 'nói'),
    (r'\bbít\b', 'biết'),
    (r'\bbit\b', 'biết'),
    (r'\bbt\b', 'biết'),
    (r'\bvaayj\b', 'vậy'),
    (r'\bzay\b', 'vậy'),
    (r'\bzậy\b', 'vậy'),
    (r'\bv\b', 'vậy'),
    (r'\bzi\b', 'gì'),
    (r'\bzì\b', 'gì'),
    (r'\bj\b', 'gì'),
    (r'\bs\b', 'sao'),
    (r'\bcug\b', 'cũng'),
    (r'\bcx\b', 'cũng'),
    (r'\bvoi\b', 'với'),
    (r'\bvs\b', 'với'),
    (r'\bnua\b', 'nữa'),
    (r'\bnx\b', 'nữa'),
    (r'\bthoai\b', 'thôi'),
    (r'\bthui\b', 'thôi'),
    (r'\bth\b', 'thôi'),
    (r'\bnt\b', 'nhắn tin'),
    (r'\bib\b', 'nhắn tin'),
    (r'\binb\b', 'nhắn tin'),

    # 3. Tính cách, Khen chê & Tình cảm
    (r'\bđth\b', 'dễ thương'),
    (r'\bdth\b', 'dễ thương'),
    (r'\bđz\b', 'đẹp trai'),
    (r'\bdz\b', 'đẹp trai'),
    (r'\bdzzz\b', 'đẹp trai'),
    (r'\bgato\b', 'ghen tị'),
    (r'\bsry\b', 'xin lỗi'),
    (r'\bsrr\b', 'xin lỗi'),
    (r'\bsr\b', 'xin lỗi'),
    (r'\bcr\b', 'crush'),
    (r'\bny\b', 'người yêu'),
    (r'\bnyc\b', 'người yêu cũ'),
    (r'\bex\b', 'người yêu cũ'),
    (r'\bvk\b', 'vợ'),
    (r'\bck\b', 'chồng'),
    (r'\bbx\b', 'bà xã'),
    (r'\box\b', 'ông xã'),

    # 4. Học tập, Cơ quan & Trường lớp
    (r'\bbtvn\b', 'bài tập về nhà'),
    (r'\bhw\b', 'bài tập về nhà'),
    (r'\bktra\b', 'kiểm tra'),
    (r'\bkt\b', 'kiểm tra'),
    (r'\btkb\b', 'thời khóa biểu'),
    (r'\bgvcn\b', 'giáo viên chủ nhiệm'),
    (r'\bgv\b', 'giáo viên'),
    (r'\bhs\b', 'học sinh'),
    (r'\bstt\b', 'số thứ tự'),
    (r'\bhc\b', 'học'),
    (r'\bca\b', 'công an'),
    (r'\bcsgt\b', 'cảnh sát giao thông'),
    (r'\bbql\b', 'ban quản lý'),

    # 5. Đại từ & Xưng hô
    (r'\bngta\b', 'người ta'),
    (r'\bnta\b', 'người ta'),
    (r'\bngừi\b', 'người'),
    (r'\bnguoi\b', 'người'),
    (r'\bng\b', 'người'),
    (r'\bae\b', 'anh em'),
    (r'\baem\b', 'anh em'),
    (r'\bmn\b', 'mọi người'),
    (r'\bmik\b', 'mình'),
    (r'\bmk\b', 'mình'),
    (r'\btui\b', 'tôi'),
    (r'\bthg\b', 'thằng'),
    (r'\bthk\b', 'thằng'),
    (r'\btk\b', 'thằng'),
    (r'\bad\b', 'admin'),
    (r'\bt\b', 'tao'),
    (r'\bm\b', 'mày'),

    # 6. Từ phủ định, đồng ý & cảm thán
    (r'\bkhong\b', 'không'),
    (r'\bhong\b', 'không'),
    (r'\bhổng\b', 'không'),
    (r'\bhok\b', 'không'),
    (r'\bhơm\b', 'không'),
    (r'\bko\b', 'không'),
    (r'\bkh\b', 'không'),
    (r'\bk0\b', 'không'),
    (r'\bk\b', 'không'),
    (r'\bkpi\b', 'không phải'),
    (r'\bkp\b', 'không phải'),
    (r'\bcbi\b', 'chuẩn bị'),
    (r'\bcb\b', 'chuẩn bị'),
    (r'\buhm\b', 'ừ'),
    (r'\bum\b', 'ừ'),
    (r'\buh\b', 'ừ'),
    (r'\buk\b', 'ừ'),
    (r'\bokela\b', 'ô kê'),
    (r'\boki\b', 'ô kê'),
    (r'\boke\b', 'ô kê'),
    (r'\bok\b', 'ô kê'),
    (r'\btks\b', 'cảm ơn'),
    (r'\bthx\b', 'cảm ơn'),
    (r'\bty\b', 'cảm ơn'),
    (r'\bcmon\b', 'cảm ơn'),
    (r'\bpls\b', 'làm ơn'),
    (r'\bplz\b', 'làm ơn'),
    (r'\bonl\b', 'on lai'),
    (r'\boff\b', 'ọp lai'),

    # 7. Mạng xã hội, Thiết bị & Game
    (r'\bđt\b', 'điện thoại'),
    (r'\bdt\b', 'điện thoại'),
    (r'\bsv\b', 'máy chủ'),
    (r'\bvc\b', 'phòng thoại'),
    (r'\bmic\b', 'míc'),
    (r'\bcam\b', 'cam-mê-ra'),
    (r'\bacc\b', 'tài khoản'),
    (r'\bpass\b', 'mật khẩu'),
    (r'\bfb\b', 'phây búc'),
    (r'\big\b', 'in-sta-gram'),
    (r'\bytb\b', 'diu túp'),
    (r'\btt\b', 'tóp tóp'),
    (r'\btiktok\b', 'tóp tóp'),
    (r'\bdis\b', 'đít cọt'),
    (r'\bdiscord\b', 'đít cọt'),
    (r'\bgame\b', 'gêm'),
    (r'\brank\b', 'ranh'),
    (r'\bnc\b', 'NoelCoin'),
    (r'\bafk\b', 'treo máy'),
    (r'\bfeed\b', 'cho mạng'),
    (r'\bgank\b', 'úp sọt'),
    (r'\bks\b', 'cướp mạng'),
    (r'\bcarry\b', 'gánh tem'),
    (r'\bnoob\b', 'gà mờ'),
    (r'\bpro\b', 'cao thủ'),
    (r'\bez\b', 'dễ ợt'),
    (r'\bgg\b', 'đầu hàng'),
    (r'\brip\b', 'an nghỉ'),
    (r'\bwtf\b', 'cái quái gì thế'),
    (r'\bwth\b', 'cái quái gì thế'),
    (r'\bomg\b', 'ôi trời ơi'),
    (r'\blmao\b', 'cười ỉa'),
    (r'\blol\b', 'cười ỉa'),
    (r'\brofl\b', 'cười lăn lộn'),
    (r'\bidk\b', 'tôi không biết'),
    (r'\bbtw\b', 'nhân tiện'),
    (r'\bbrb\b', 'quay lại ngay'),
]

def clean_text_for_tts(text: str) -> str:
    """Loại bỏ link, emoji phức tạp, dịch teencode và nói lái từ tục"""
    # 1. Bỏ URL link
    text = re.sub(r'https?://\S+|www\.\S+', 'gửi một đường linh', text)
    # 2. Bỏ Custom Discord Emoji <:name:id>
    text = re.sub(r'<a?:[a-zA-Z0-9_]+:[0-9]+>', '', text)
    # 3. Dịch viết tắt, teencode & nói lái từ tục
    for pattern, replacement in VIETNAMESE_ABBREVIATIONS:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    # 4. Xóa khoảng trắng thừa
    text = re.sub(r'\s+', ' ', text).strip()
    return text


class VoiceTTSCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.voice_name = "vi-VN-HoaiMyNeural"
        self.auto_tts_enabled = True
        self.tts_queue = asyncio.Queue()
        self.is_playing = False
        self.worker_task = None

    async def cog_load(self):
        self.worker_task = asyncio.create_task(self.queue_worker())
        logger.info("Auto-TTS Queue Worker đã khởi động thành công.")

    def cog_unload(self):
        if self.worker_task:
            self.worker_task.cancel()

    async def queue_worker(self):
        while True:
            try:
                guild_id, text_to_speak, voice_client = await self.tts_queue.get()
                if voice_client and voice_client.is_connected():
                    await self._play_audio(voice_client, text_to_speak)
                self.tts_queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Lỗi trong TTS queue worker: {e}", exc_info=True)
                await asyncio.sleep(0.5)

    async def _play_audio(self, voice_client: discord.VoiceClient, text: str):
        temp_file = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        temp_path = temp_file.name
        temp_file.close()

        try:
            communicate = edge_tts.Communicate(text, self.voice_name)
            await communicate.save(temp_path)

            ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
            
            while voice_client.is_playing():
                await asyncio.sleep(0.3)

            play_done_event = asyncio.Event()

            def after_playing(error):
                if error:
                    logger.error(f"TTS Playback error: {error}")
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except Exception:
                        pass
                self.bot.loop.call_soon_threadsafe(play_done_event.set)

            source = discord.FFmpegPCMAudio(temp_path, executable=ffmpeg_path)
            voice_client.play(source, after=after_playing)

            await play_done_event.wait()
        except Exception as e:
            logger.error(f"Lỗi khi phát âm thanh TTS: {e}", exc_info=True)
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass

    # ================= LẮNG NGHE CHAT ĐỂ TỰ ĐỘNG ĐỌC =================
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        if not self.auto_tts_enabled:
            return

        if message.content.startswith(("!", "/", "$")):
            return

        voice_client = message.guild.voice_client
        if not voice_client or not voice_client.is_connected():
            return

        bot_channel = voice_client.channel
        is_in_vc_chat = (message.channel.id == bot_channel.id)

        if not is_in_vc_chat and isinstance(message.author, discord.Member):
            if message.author.voice and message.author.voice.channel == bot_channel:
                is_in_vc_chat = True

        if is_in_vc_chat:
            raw_text = message.clean_content
            clean_text = clean_text_for_tts(raw_text)
            if not clean_text:
                return

            if len(clean_text) > 600:
                clean_text = clean_text[:600] + " và còn nhiều chữ nữa..."

            speech_text = f"{message.author.display_name} nói: {clean_text}"
            await self.tts_queue.put((message.guild.id, speech_text, voice_client))

    # ================= SLASH COMMANDS =================
    @app_commands.command(name="join", description="Gọi chị Google vào kênh voice và tự động đọc chat")
    async def join(self, interaction: discord.Interaction):
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message(
                "❌ Mày phải vào phòng voice trước rồi mới gọi tao vào được chứ con lợn!",
                ephemeral=True
            )
            return

        voice_channel = interaction.user.voice.channel
        voice_client = interaction.guild.voice_client

        if voice_client and voice_client.is_connected():
            if voice_client.channel.id == voice_channel.id:
                await interaction.response.send_message(
                    f"🔊 Tao đang ở trong kênh **{voice_channel.name}** rồi! Cứ chat trong này tao tự động đọc hết!",
                    ephemeral=True
                )
                return
            else:
                await voice_client.move_to(voice_channel)
        else:
            voice_client = await voice_channel.connect()

        embed = discord.Embed(
            title="🎙️ CHỊ GOOGLE ĐÃ VÀO PHÒNG VOICE! 🔊",
            description=f"✅ Đã kết nối vào **{voice_channel.name}**.\n\n"
                        f"✨ **Tự Động Đọc Chat (Auto-TTS):** `BẬT`\n"
                        f"👉 Ai không bật mic chỉ cần **gõ chữ trong chat của phòng này**, chị Google sẽ tự động đọc thay bạn từng câu trôi chảy!",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="leave", description="Đuổi chị Google rời khỏi kênh voice")
    async def leave(self, interaction: discord.Interaction):
        voice_client = interaction.guild.voice_client
        if not voice_client or not voice_client.is_connected():
            await interaction.response.send_message("❌ Tao có ở trong phòng voice nào đâu mà đuổi?", ephemeral=True)
            return

        await voice_client.disconnect()
        await interaction.response.send_message("👋 Chị đi đây, lũ hề ở lại vui vẻ nhé!")

    @app_commands.command(name="noi", description="Chị Google đọc ngay câu này trong voice")
    async def noi(self, interaction: discord.Interaction, noi_dung: str):
        voice_client = interaction.guild.voice_client
        if not voice_client or not voice_client.is_connected():
            await interaction.response.send_message(
                "❌ Bot chưa vào kênh voice! Hãy dùng `/join` hoặc `!join` trước nhé.",
                ephemeral=True
            )
            return

        clean_text = clean_text_for_tts(noi_dung)
        speech_text = f"{interaction.user.display_name} nói: {clean_text}"
        await self.tts_queue.put((interaction.guild.id, speech_text, voice_client))
        await interaction.response.send_message(f"🗣️ Đã đưa vào hàng chờ đọc: *{clean_text}*", ephemeral=True)

    @commands.command(name="join")
    async def cmd_join(self, ctx):
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send("❌ Mày phải vào phòng voice trước rồi mới gọi tao vào được!")
            return
        voice_channel = ctx.author.voice.channel
        voice_client = ctx.guild.voice_client
        if voice_client and voice_client.is_connected():
            await voice_client.move_to(voice_channel)
        else:
            await voice_channel.connect()
        await ctx.send(f"🔊 Chị Google đã vào phòng **{voice_channel.name}**! Ai câm mic cứ chat tao đọc hộ!")

    @commands.command(name="leave")
    async def cmd_leave(self, ctx):
        voice_client = ctx.guild.voice_client
        if voice_client and voice_client.is_connected():
            await voice_client.disconnect()
            await ctx.send("👋 Chị đi đây!")


async def setup(bot):
    await bot.add_cog(VoiceTTSCog(bot))
