import os
import re
import asyncio
import tempfile
from pathlib import Path

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
import yt_dlp


BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN غير موجود في متغيرات البيئة")


def get_youtube_url(text):
    pattern = r"https?://(?:www\.)?(?:youtube\.com/watch\?v=[\w-]+|youtu\.be/[\w-]+|youtube\.com/shorts/[\w-]+)"
    match = re.search(pattern, text)
    return match.group(0) if match else None


def download_video(url, folder):
    output = str(Path(folder) / "%(title).80s.%(ext)s")

    options = {
        "format": "best[ext=mp4][height<=720]/best[height<=720]/best",
        "outtmpl": output,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "merge_output_format": "mp4",
    }

    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)

        # yt-dlp قد يغير الامتداد بعد الدمج إلى mp4
        mp4_file = Path(filename).with_suffix(".mp4")

        if mp4_file.exists():
            return str(mp4_file)

        if Path(filename).exists():
            return filename

        files = list(Path(folder).glob("*"))
        if files:
            return str(files[0])

        raise FileNotFoundError("لم يتم العثور على الفيديو")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎬 أهلاً بيك!\n\n"
        "ابعتلي رابط فيديو من YouTube وأنا هحملهولك.\n\n"
        "مثال:\n"
        "https://www.youtube.com/watch?v=xxxxxxxxxxx"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""
    url = get_youtube_url(text)

    if not url:
        await update.message.reply_text(
            "❌ ابعت رابط YouTube صحيح."
        )
        return

    status = await update.message.reply_text(
        "⏳ جاري تحميل الفيديو...\n"
        "استنى شوية."
    )

    try:
        with tempfile.TemporaryDirectory() as temp_dir:

            video_file = await asyncio.to_thread(
                download_video,
                url,
                temp_dir
            )

            file_size = os.path.getsize(video_file)

            # حد احتياطي للملفات الكبيرة
            if file_size > 49 * 1024 * 1024:
                await status.edit_text(
                    "❌ الفيديو أكبر من الحد المسموح للإرسال عبر البوت."
                )
                return

            await status.edit_text(
                "📤 تم التحميل!\n"
                "جاري إرسال الفيديو..."
            )

            with open(video_file, "rb") as video:
                await update.message.reply_video(
                    video=video,
                    caption="🎬 تم التحميل بواسطة البوت",
                    supports_streaming=True,
                    read_timeout=120,
                    write_timeout=120,
                    connect_timeout=60,
                )

            await status.delete()

    except Exception as e:
        print("ERROR:", e)

        try:
            await status.edit_text(
                "❌ حصل خطأ أثناء تحميل الفيديو.\n\n"
                "تأكد إن الرابط شغال وحاول تاني."
            )
        except Exception:
            pass


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 طريقة الاستخدام:\n\n"
        "1️⃣ اضغط /start\n"
        "2️⃣ ابعت رابط YouTube\n"
        "3️⃣ استنى التحميل\n"
        "4️⃣ البوت هيبعتلك الفيديو 🎬"
    )


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message
        )
    )

    print("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()