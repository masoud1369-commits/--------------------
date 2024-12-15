import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackContext, CallbackQueryHandler, filters
from pytube import YouTube
import os
import time

# تنظیمات ربات
TOKEN = '8023249611:AAFRiRypVo6BSt-N3vL0dtzMz4F0NgX_10Q'
DOWNLOAD_PATH = './downloads/'
MAX_CONCURRENT_DOWNLOADS = 2  # حداکثر تعداد دانلود هم‌زمان

# ایجاد پوشه دانلود در صورت عدم وجود
if not os.path.exists(DOWNLOAD_PATH):
    os.makedirs(DOWNLOAD_PATH)

# ذخیره لینک‌ها و زمان اعتبار آن‌ها
active_links = {}

# تابع خوش‌آمدگویی
async def start(update: Update, context: CallbackContext) -> None:
    keyboard = [
        [InlineKeyboardButton("راهنما", callback_data='help')],
        [InlineKeyboardButton("ارسال لینک دانلود", callback_data='send_link')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        'سلام! به ربات دانلود یوتیوب خوش آمدید. یکی از گزینه‌های زیر را انتخاب کنید:',
        reply_markup=reply_markup
    )

# تابع راهنما
async def help_command(update: Update, context: CallbackContext) -> None:
    await update.callback_query.message.reply_text(
        'این ربات به شما کمک می‌کند تا ویدیوهای یوتیوب را دانلود کنید. کافیست لینک یوتیوب را ارسال کنید.'
    )

# پاسخ به کلیک دکمه‌ها
async def button_handler(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()

    if query.data == 'help':
        await help_command(update, context)
    elif query.data == 'send_link':
        await query.message.reply_text('لطفاً لینک ویدیو یوتیوب را ارسال کنید.')

# تابع افزودن لینک به صف
async def queue_video(update: Update, context: CallbackContext) -> None:
    url = update.message.text
    if not url.startswith("http"):
        await update.message.reply_text('لینک معتبر نیست. لطفاً یک لینک یوتیوب ارسال کنید.')
        return

    # بررسی اگر لینک قبلاً در دسترس است
    if url in active_links and time.time() - active_links[url] < 86400:  # اعتبار 24 ساعته
        await update.message.reply_text('این لینک قبلاً اضافه شده است و هنوز معتبر است.')
        return

    # بررسی وضعیت ویدیو
    try:
        yt = YouTube(url)
        yt.check_availability()
        active_links[url] = time.time()  # ذخیره لینک و زمان فعلی
        await update.message.reply_text(f'لینک شما به صف دانلود اضافه شد. مدت زمان اعتبار آن 24 ساعت است.')
    except Exception as e:
        await update.message.reply_text(f'خطایی در بررسی لینک رخ داد: {e}')

# تابع دانلود ویدئو
async def download_video(update: Update, url: str) -> None:
    try:
        yt = YouTube(url)
        video = yt.streams.filter(progressive=True, file_extension='mp4').first()
        if not video:
            await update.message.reply_text('خطایی در یافتن ویدیو: ممکن است فرمت مورد نظر موجود نباشد.')
            return

        file_path = video.download(output_path=DOWNLOAD_PATH)

        await update.message.reply_text('دانلود کامل شد! در حال ارسال فایل...')
        with open(file_path, 'rb') as video_file:
            await update.message.reply_video(video_file)

        os.remove(file_path)  # حذف فایل پس از ارسال
    except Exception as e:
        await update.message.reply_text(f'خطایی رخ داد: {e}')

# پردازش صف
async def process_queue() -> None:
    while True:
        for url in list(active_links.keys()):
            # بررسی اعتبار لینک
            if time.time() - active_links[url] >= 86400:  # اعتبار 24 ساعته
                del active_links[url]  # حذف لینک‌های منقضی‌شده
        await asyncio.sleep(60)  # هر 60 ثانیه یکبار بررسی کنید

# تابع اصلی برای راه‌اندازی ربات
async def main() -> None:
    app = ApplicationBuilder().token(TOKEN).build()

    # مدیریت دستورات
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, queue_video))

    # اجرای پردازش صف به صورت موازی
    asyncio.create_task(process_queue())
    
    # راه‌اندازی ربات
    await app.run_polling()

if __name__ == '__main__':
    # استفاده از await به جای asyncio.run
    asyncio.run(main())
