import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, CallbackContext
import speedtest
import random

# فعال‌سازی لاگینگ
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = '8023249611:AAFRiRypVo6BSt-N3vL0dtzMz4F0NgX_10Q'  # توکن ربات تلگرام
YOUTUBE_API_KEY = 'AIzaSyBhwd2T6v4wSlEV69euIUfnUlrmknynS2g'  # کلید API YouTube
session = requests.Session()

# نگه‌داری نتایج جستجوی اخیر برای هر کاربر
user_search_results = {}

# استیکرهای مختلف که می‌توانند در ربات استفاده شوند
stickers = [
    "CAACAgUAAxkBAAIBF2VXh0eDB1fIWGqKYt0WqiyBco_XAAmZAQACgwIAAmHrwZ3Jf0kHk0gE",
    "CAACAgUAAxkBAAIBF2JXh0eDB1fIWGqKYt0WqiyBco_XAAmZAQACgwIAAmHrwZ3Jf0kHk0gE"
]

# تابعی برای گرفتن سرعت اینترنت کاربر
def check_internet_speed():
    st = speedtest.Speedtest()
    st.get_best_server()
    download_speed = st.download() / 1_000_000  # تبدیل به مگابیت بر ثانیه
    ping = st.results.ping
    return download_speed, ping

# دستور /start (بدون دکمه‌ها و منوی جدید)
async def send_welcome(update: Update, context: CallbackContext):
    logger.info("Handling /start command")
    
    # ارسال استیکر قبل از پیام خوشامدگویی
    sticker_id = random.choice(stickers)  # انتخاب یک استیکر تصادفی از لیست
    await update.message.reply_sticker(sticker_id)
    
    # پیام خوشامدگویی
    await update.message.reply_text(
        "سلام! من ربات جستجوگر یوتیوبم! 😎\n"
        "با من می‌تونی ویدیوهای یوتیوب رو پیدا کنی و دانلود کنی.\n"
        "لطفاً نام ویدیو مورد نظر خود را ارسال کن تا شروع به جستجو کنم!"
    )

# دستور /help
async def send_help(update: Update, context: CallbackContext):
    logger.info("Handling /help command")
    help_text = (
        "📚 <b>دستورالعمل‌های ربات:</b>\n\n"
        "1. <b>/start:</b> برای شروع به جستجو، فقط نام ویدیو رو ارسال کن.\n"
        "2. <b>/help:</b> برای دیدن دستورالعمل‌های من.\n"
        "3. <b>/search [نام ویدیو]:</b> جستجو برای ویدیوها در یوتیوب.\n"
        "   - برای مثال: /search گربه‌های خنده‌دار 😹\n"
        "4. انتخاب یک ویدیو و دریافت لینک دانلود.\n"
        "5. بله یا خیر؟ آیا سرعت اینترنت و پینگ شما رو می‌خواهید ببینید؟ 🤔"
    )
    # ارسال استیکر در پاسخ به کمک
    sticker_id = random.choice(stickers)
    await update.message.reply_sticker(sticker_id)

    await update.message.reply_text(help_text, parse_mode="HTML")

# دستور /search
async def search_video(update: Update, context: CallbackContext):
    logger.info("Handling /search command")
    video_name = update.message.text  # از متن پیام ارسال شده توسط کاربر استفاده می‌کنیم

    if not video_name:
        logger.warning("No video name provided in /search command")
        await update.message.reply_text("🤔 ای بابا! نام ویدیو رو فراموش کردی وارد کنی؟")
        return

    try:
        logger.info(f"Searching for video: {video_name}")
        response = session.get("https://www.googleapis.com/youtube/v3/search", params={
            'part': 'snippet',
            'q': video_name,
            'key': YOUTUBE_API_KEY,
            'maxResults': 8
        })

        if response.status_code != 200:
            logger.error(f"YouTube API request failed with status code {response.status_code}")
            await update.message.reply_text(f"😢 وای! یه مشکلی پیش اومد. وضعیت درخواست: {response.status_code}")
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
                user_search_results[update.message.chat_id] = video_results
                await display_search_results(update, context, video_results)
            else:
                await update.message.reply_text("😕 هیچی پیدا نکردیم! دوباره تلاش کن.")
        else:
            await update.message.reply_text("😔 هیچ ویدیویی پیدا نشد.")
    except requests.exceptions.RequestException as e:
        logger.error(f"Request to YouTube API failed: {e}")
        await update.message.reply_text("🚫 مشکل در اتصال به YouTube API.")

# نمایش نتایج جستجو
async def display_search_results(update: Update, context: CallbackContext, video_results):
    logger.info("Displaying search results to user")
    keyboard = [
        [InlineKeyboardButton(f"{i+1}. {video['title']} 🎥", callback_data=f"video_{i}")] 
        for i, video in enumerate(video_results)
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # ارسال استیکر پس از نمایش نتایج جستجو
    sticker_id = random.choice(stickers)  # انتخاب استیکر تصادفی
    await update.message.reply_sticker(sticker_id)

    await update.message.reply_text(
        "🎥 ویدیوهای پیدا شده:\n\nلطفاً یک ویدیو رو انتخاب کن که دانلودش کنی!\n",
        reply_markup=reply_markup
    )

# ارسال لینک دانلود اصلاح‌شده با پیش‌نمایش
async def send_modified_link(update: Update, context: CallbackContext):
    query = update.callback_query
    try:
        video_index = int(query.data.split("_")[1])
        selected_video = user_search_results[query.message.chat_id][video_index]
        logger.info(f"User selected video: {selected_video['title']}")

        original_url = selected_video['url']
        modified_url = original_url.replace("youtube.com", "youtubepp.com")

        preview_text = (
            f"✅ ویدیو انتخابی شما: <b>{selected_video['title']}</b>\n\n"
            f"🔗 <a href='{original_url}'>پیش‌نمایش ویدیو</a>"
        )
        await query.message.reply_text(preview_text, parse_mode="HTML")

        final_text = (
            f"✅ ویدیو شما: <b>{selected_video['title']}</b>\n\n"
            f"⬇️ روی لینک زیر بزنید تا وارد صفحه دانلود شوید:\n\n"
            f"🔗 <a href='{modified_url}'>{modified_url}</a>"
        )
        await query.message.reply_text(final_text, parse_mode="HTML")

        # از کاربر می‌خواهیم که آیا می‌خواهد سرعت اینترنت و پینگ خود را مشاهده کند یا خیر
        await ask_for_speed_check(query)

        await query.answer()

    except IndexError:
        logger.error("Invalid video selection.")
        await query.message.edit_text("❌ انتخاب نامعتبر، لطفاً دوباره تلاش کن.")
        await query.answer()

# از کاربر می‌خواهیم که آیا می‌خواهد سرعت اینترنت و پینگ را مشاهده کند یا خیر
async def ask_for_speed_check(query):
    keyboard = [
        [InlineKeyboardButton("بله 👍", callback_data='check_speed')],
        [InlineKeyboardButton("خیر 👎", callback_data='no_speed')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text("آیا می‌خواهید سرعت اینترنت و پینگ خود را مشاهده کنید؟", reply_markup=reply_markup)

# ایجاد یک آبجکت برنامه
async def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", send_welcome))
    application.add_handler(CommandHandler("help", send_help))
    application.add_handler(CommandHandler("search", search_video))
    application.add_handler(CallbackQueryHandler(send_modified_link, pattern=r"^video_"))
    application.add_handler(CallbackQueryHandler(ask_for_speed_check, pattern=r"^check_speed"))
    
    # اجرای برنامه به صورت polling
    await application.run_polling()

# شروع اجرای برنامه
if __name__ == "__main__":
    main()
