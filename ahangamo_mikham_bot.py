import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, CallbackContext
import asyncio

# فعال‌سازی لاگینگ
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = '8023249611:AAFRiRypVo6BSt-N3vL0dtzMz4F0NgX_10Q'  # توکن ربات تلگرام
YOUTUBE_API_KEY = 'AIzaSyBhwd2T6v4wSlEV69euIUfnUlrmknynS2g'  # کلید API YouTube
session = requests.Session()

# نگه‌داری نتایج جستجوی اخیر برای هر کاربر
user_search_results = {}

# دستور /start
async def send_welcome(update: Update, context: CallbackContext):
    logger.info("Handling /start command")
    keyboard = [
        [InlineKeyboardButton("شروع", callback_data='start')],
        [InlineKeyboardButton("راهنما", callback_data='help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "سلام! از این ربات برای جستجو و دانلود ویدیوهای یوتیوب استفاده کنید. برای شروع دکمه 'شروع' را بزنید.",
        reply_markup=reply_markup
    )

# دستور /help
async def send_help(update: Update, context: CallbackContext):
    logger.info("Handling /help command")
    help_text = (
        "دستورها:\n\n"
        "1. /start: شروع به کار با ربات.\n"
        "2. /help: نمایش دستورالعمل‌های استفاده.\n"
        "3. /search [نام ویدیو]: جستجو برای ویدیوها در یوتیوب.\n"
        "   - مثال: /search گربه‌های خنده‌دار\n"
        "4. انتخاب یک ویدیو و دریافت لینک دانلود آن."
    )

    await update.message.reply_text(help_text)

# دستور /search
async def search_video(update: Update, context: CallbackContext):
    logger.info("Handling /search command")
    video_name = ' '.join(context.args) if context.args else None
    if not video_name:
        logger.warning("No video name provided in /search command")
        await update.message.reply_text("لطفاً نام ویدیو را برای جستجو وارد کنید.")
        return

    try:
        logger.info(f"Searching for video: {video_name}")
        response = session.get("https://www.googleapis.com/youtube/v3/search", params={
            'part': 'snippet',
            'q': video_name,
            'key': YOUTUBE_API_KEY,
            'maxResults': 5
        })

        if response.status_code != 200:
            logger.error(f"YouTube API request failed with status code {response.status_code}")
            await update.message.reply_text(f"خطا در دریافت داده‌ها از YouTube API. وضعیت: {response.status_code}")
            return

        data = response.json()
        video_results = []

        if 'items' in data and data['items']:
            logger.info("Parsing search results from YouTube API response")
            for item in data['items']:
                video_title = item['snippet']['title']
                video_id = item['id'].get('videoId', None)

                if video_id:
                    video_url = f"https://www.youtube.com/watch?v={video_id}"
                    video_results.append({
                        'title': video_title,
                        'url': video_url,
                        'id': video_id
                    })

            if video_results:
                logger.info("Search results found and stored")
                user_search_results[update.message.chat_id] = video_results
                await display_search_results(update, context, video_results)
            else:
                logger.warning("No suitable videos found in search results")
                await update.message.reply_text("هیچ ویدیوی مناسبی پیدا نشد.")
        else:
            logger.warning("No videos found in search response")
            await update.message.reply_text("هیچ ویدیویی پیدا نشد.")
    except requests.exceptions.RequestException as e:
        logger.error(f"Request to YouTube API failed: {e}")
        await update.message.reply_text("خطا در اتصال به YouTube API.")

# نمایش نتایج جستجو
async def display_search_results(update: Update, context: CallbackContext, video_results):
    logger.info("Displaying search results to user")
    keyboard = [
        [InlineKeyboardButton(f"{i+1}. {video['title']}", callback_data=f"video_{i}")]
        for i, video in enumerate(video_results)
    ]
    keyboard.append([InlineKeyboardButton("🔄 جستجوی جدید", callback_data='new_search')])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "لطفاً یک ویدیو را انتخاب کنید:",
        reply_markup=reply_markup
    )

# ارسال لینک دانلود اصلاح‌شده با پیش‌نمایش
async def send_modified_link(update: Update, context: CallbackContext):
    query = update.callback_query
    try:
        video_index = int(query.data.split("_")[1])
        selected_video = user_search_results[query.message.chat_id][video_index]
        logger.info(f"User selected video: {selected_video['title']}")

        # تغییر آدرس ویدیو به لینک قابل دانلود مشابه با utjetbot
        original_url = selected_video['url']
        modified_url = original_url.replace("youtube.com", "youtubepp.com")

        # ارسال لینک ویدیو به عنوان پیش‌نمایش
        preview_text = (
            f"✅ ویدیو مورد نظر شما: <b>{selected_video['title']}</b>\n\n"
            f"🔗 این لینک را برای پیش‌نمایش و مشاهده ویدیو امتحان کنید:\n\n"
            f"🔗 <a href='{original_url}'>پیش‌نمایش ویدیو</a>"
        )
        preview_message = await query.message.reply_text(preview_text, parse_mode="HTML")

        # ارسال لینک نهایی دانلود بعد از 2 ثانیه
        await asyncio.sleep(2)
        final_text = (
            f"✅ ویدیو مورد نظر شما: <b>{selected_video['title']}</b>\n\n"
            f"⬇️ <b>روی لینک زیر بزنید</b> تا وارد صفحه دانلود شوید و بتوانید ویدیو را با کیفیت‌های مختلف دانلود کنید:\n\n"
            f"🔗 <a href='{modified_url}'>{modified_url}</a>"
        )

        # ارسال لینک نهایی به صورت جداگانه
        await query.message.reply_text(final_text, parse_mode="HTML")
        await query.answer()

    except IndexError:
        logger.error("Invalid video selection.")
        await query.message.edit_text("❌ انتخاب نامعتبر، لطفاً دوباره تلاش کنید.")
        await query.answer()
    except Exception as e:
        logger.error(f"Error modifying the download link: {e}")
        await query.message.edit_text("❌ ارسال لینک دانلود با شکست مواجه شد. لطفاً بعداً دوباره تلاش کنید.")
        await query.answer()

# پیکربندی و اجرای ربات
def main():
    logger.info("Starting the bot application")
    application = Application.builder().token(TOKEN).build()

    # ثبت هندلرها
    application.add_handler(CommandHandler("start", send_welcome))
    application.add_handler(CommandHandler("help", send_help))
    application.add_handler(CommandHandler("search", search_video))
    application.add_handler(CallbackQueryHandler(send_modified_link, pattern=r"video_\d+"))
    application.add_handler(CallbackQueryHandler(search_video, pattern='new_search'))

    # اجرای ربات
    application.run_polling()

if __name__ == "__main__":
    main()