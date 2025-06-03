import os
import logging
from flask import Flask, request, abort
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler
from dotenv import load_dotenv # শুধু লোকাল ডেভেলপমেন্টের জন্য
import asyncio # <--- এই লাইনটি যোগ করা হয়েছে

# --- কনফিগারেশন শুরু ---
# .env ফাইল থেকে ভ্যারিয়েবল লোড করবে (যদি থাকে, Render-এ এটি লাগবে না)
load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
WEB_APP_URL = os.getenv('WEB_APP_URL') # আপনার ওয়েবসাইটের URL
RENDER_APP_URL = os.getenv('RENDER_APP_URL') # যেমন: https://your-app-name.onrender.com

# লগিং কনফিগারেশন
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# যে চ্যানেলগুলোতে জয়েন করতে হবে
REQUIRED_CHANNELS = [
    {
        'id': '@global_Fun22', # চ্যানেল ইউজারনেম (@ সহ)
        'name': 'Global Fun',
        'url': 'https://t.me/global_Fun22'
    },
    {
        'id': '@instant_earn_airdrop',
        'name': 'Instant Earn Airdrop',
        'url': 'https://t.me/instant_earn_airdrop'
    },
    {
        'id': '@myearn_Cash_payment',
        'name': 'MyEarn Cash Payment',
        'url': 'https://t.me/myearn_Cash_payment'
    }
]
# --- কনফিগারেশন শেষ ---

# Flask অ্যাপ ইনিশিয়ালাইজেশন
app = Flask(__name__)

# টেলিগ্রাম অ্যাপ্লিকেশন বিল্ডার
if not BOT_TOKEN:
    logger.error("BOT_TOKEN এনভায়রনমেন্ট ভ্যারিয়েবল সেট করা নেই!")
    ptb_application = None
else:
    ptb_application = Application.builder().token(BOT_TOKEN).build()

async def check_user_membership(user_id: int, chat_id: str, context: CallbackContext) -> bool:
    """নির্দিষ্ট চ্যানেলে ব্যবহারকারীর সদস্যপদ চেক করে"""
    try:
        member = await context.bot.get_chat_member(chat_id=chat_id, user_id=user_id)
        if member.status in ['member', 'administrator', 'creator']:
            return True
        logger.info(f"User {user_id} is '{member.status}' in channel {chat_id}")
        return False
    except Exception as e:
        logger.error(f"Error checking membership for user {user_id} in channel {chat_id}: {e}")
        return False

async def start_command(update: Update, context: CallbackContext) -> None:
    """/start কমান্ড হ্যান্ডেল করে"""
    user = update.effective_user
    if not user:
        logger.warning("No user found in update for /start command.")
        return

    user_id = user.id
    chat_id = update.effective_chat.id

    not_joined_channels = []
    all_joined = True

    for channel in REQUIRED_CHANNELS:
        is_member = await check_user_membership(user_id, channel['id'], context)
        if not is_member:
            all_joined = False
            not_joined_channels.append(channel)

    if all_joined:
        welcome_message = "ধন্যবাদ! আপনি প্রয়োজনীয় সকল চ্যানেলে জয়েন করেছেন।\n\n" \
                          "এবার আমাদের ওয়েবসাইট ভিজিট করুন:"
        keyboard = [
            [InlineKeyboardButton("🌐 ওয়েবসাইট ভিজিট করুন", web_app=WebAppInfo(url=WEB_APP_URL))]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_html(text=welcome_message, reply_markup=reply_markup)
    else:
        join_message = "বটটি ব্যবহার করার জন্য অনুগ্রহ করে নিচের চ্যানেলগুলোতে জয়েন করুন:\n\n"
        inline_keyboard_buttons = []

        for channel_info in not_joined_channels:
            join_message += f"➡️ <b>{channel_info['name']}</b>\n"
            inline_keyboard_buttons.append(
                [InlineKeyboardButton(f"🔗 {channel_info['name']}", url=channel_info['url'])]
            )
        
        join_message += "\nসবগুলো চ্যানেলে জয়েন করার পর নিচের বাটনে ক্লিক করুন।"
        inline_keyboard_buttons.append(
            [InlineKeyboardButton("✅ আমি জয়েন করেছি / রিচেক", callback_data='check_join_status')]
        )
        reply_markup = InlineKeyboardMarkup(inline_keyboard_buttons)
        await update.message.reply_html(text=join_message, reply_markup=reply_markup)

async def button_callback_handler(update: Update, context: CallbackContext) -> None:
    """ইনলাইন বাটনের কলব্যাক হ্যান্ডেল করে"""
    query = update.callback_query
    await query.answer() 

    if query.data == 'check_join_status':
        user_id = query.from_user.id
        chat_id = query.message.chat_id
        
        not_joined_channels = []
        all_joined = True

        for channel in REQUIRED_CHANNELS:
            is_member = await check_user_membership(user_id, channel['id'], context)
            if not is_member:
                all_joined = False
                not_joined_channels.append(channel)

        if all_joined:
            welcome_message = "ধন্যবাদ! আপনি প্রয়োজনীয় সকল চ্যানেলে জয়েন করেছেন।\n\n" \
                              "এবার আমাদের ওয়েবসাইট ভিজিট করুন:"
            keyboard = [
                [InlineKeyboardButton("🌐 ওয়েবসাইট ভিজিট করুন", web_app=WebAppInfo(url=WEB_APP_URL))]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await context.bot.send_message(chat_id=chat_id, text=welcome_message, reply_markup=reply_markup, parse_mode='HTML')
        else:
            join_message = "আপনি এখনও নিচের চ্যানেলগুলোতে জয়েন করেননি:\n\n"
            inline_keyboard_buttons = []
            for channel_info in not_joined_channels:
                join_message += f"➡️ <b>{channel_info['name']}</b>\n"
                inline_keyboard_buttons.append(
                    [InlineKeyboardButton(f"🔗 {channel_info['name']}", url=channel_info['url'])]
                )
            join_message += "\nঅনুগ্রহ করে সবগুলোতে জয়েন করে আবার 'রিচেক' বাটনে ক্লিক করুন।"
            inline_keyboard_buttons.append(
                [InlineKeyboardButton("✅ আমি জয়েন করেছি / রিচেক", callback_data='check_join_status')]
            )
            reply_markup = InlineKeyboardMarkup(inline_keyboard_buttons)
            try:
                await query.edit_message_text(text=join_message, reply_markup=reply_markup, parse_mode='HTML')
            except Exception as e: 
                logger.error(f"Could not edit message: {e}")
                await context.bot.send_message(chat_id=chat_id, text=join_message, reply_markup=reply_markup, parse_mode='HTML')


# Flask রুট: Webhook রিসিভ করার জন্য
@app.route('/webhook', methods=['POST'])
async def webhook(): # এই রুটটি async থাকতে পারে
    if request.method == "POST":
        if ptb_application is None:
            logger.error("PTB Application is not initialized. BOT_TOKEN might be missing.")
            abort(500) # অথবা অন্য কোনো উপযুক্ত এরর কোড

        json_data = request.get_json()
        if not json_data:
            logger.warning("Received empty JSON data.")
            abort(400)
        
        update = Update.de_json(json_data, ptb_application.bot)
        logger.info(f"Received update: {update.update_id}")
        await ptb_application.process_update(update)
        return '', 200 
    else:
        abort(400)

# Flask রুট: Webhook সেট করার জন্য (শুধু একবার রান করতে হবে)
@app.route('/set_webhook', methods=['GET'])
def set_webhook(): # <--- 'async def' থেকে 'def' করা হয়েছে
    if ptb_application is None:
        return "Telegram Application শুরু করা যায়নি (BOT_TOKEN সমস্যা?)", 500
    if not RENDER_APP_URL:
        return "RENDER_APP_URL এনভায়রনমেন্ট ভ্যারিয়েবল সেট করা নেই!", 500
    
    webhook_url = f"{RENDER_APP_URL.rstrip('/')}/webhook" # ট্রেইলিং স্ল্যাশ থাকলে বাদ দেওয়া হয়েছে
    
    async def _set_webhook_async(): # <--- একটি নেস্টেড async ফাংশন তৈরি করা হয়েছে
        return await ptb_application.bot.set_webhook(url=webhook_url, allowed_updates=["message", "callback_query"])

    try:
        # asyncio.run() ব্যবহার করে async ফাংশন কল করা হচ্ছে
        # Gunicorn এর জন্য একটি নতুন ইভেন্ট লুপ তৈরি করা ভালো
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        success = loop.run_until_complete(_set_webhook_async())
        
        if success:
            return f"Webhook সফলভাবে সেট করা হয়েছে: {webhook_url}", 200
        else:
            # Webhook সেটআপ ফেইল হলে টেলিগ্রাম থেকে পাওয়া রেসপন্স লগ করা যেতে পারে
            # info = await ptb_application.bot.get_webhook_info()
            # logger.error(f"Webhook সেট করতে ব্যর্থ! Info: {info}")
            return "Webhook সেট করতে ব্যর্থ!", 500
    except RuntimeError as e: # যেমন: "asyncio.run() cannot be called from a running event loop"
        logger.error(f"Webhook সেট করতে RuntimeError (সম্ভবত Gunicorn ইভেন্ট লুপের সাথে কনফ্লিক্ট): {e}")
        # এক্ষেত্রে আমরা সরাসরি ptb_application এর ইভেন্ট লুপ ব্যবহার করার চেষ্টা করতে পারি
        try:
            if ptb_application and hasattr(ptb_application, 'loop') and ptb_application.loop.is_running():
                 future = asyncio.run_coroutine_threadsafe(_set_webhook_async(), ptb_application.loop)
                 success = future.result(timeout=10) # ১০ সেকেন্ড পর্যন্ত অপেক্ষা করবে
                 if success:
                     return f"Webhook সফলভাবে সেট করা হয়েছে (থ্রেডসেফ): {webhook_url}", 200
                 else:
                     return "Webhook সেট করতে ব্যর্থ (থ্রেডসেফ)!", 500
            else: # ফলব্যাক
                 logger.warning("PTB application loop is not available or not running for threadsafe call.")
                 return f"Webhook সেট করতে সমস্যা: {e} (PTB loop unavailable for threadsafe)", 500
        except Exception as ex_inner:
            logger.error(f"Webhook সেট করতে থ্রেডসেফ পদ্ধতিতে সমস্যা: {ex_inner}")
            return f"Webhook সেট করতে সমস্যা (থ্রেডসেফ): {ex_inner}", 500

    except Exception as e:
        logger.error(f"Webhook সেট করতে সাধারণ সমস্যা: {e}")
        return f"Webhook সেট করতে সাধারণ সমস্যা: {e}", 500

@app.route('/delete_webhook', methods=['GET'])
def delete_webhook_route(): # <--- 'async def' থেকে 'def' করা হয়েছে
    if ptb_application is None:
        return "Telegram Application শুরু করা যায়নি (BOT_TOKEN সমস্যা?)", 500

    async def _delete_webhook_async(): # <--- একটি নেস্টেড async ফাংশন
        return await ptb_application.bot.delete_webhook()
        
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        success = loop.run_until_complete(_delete_webhook_async())
        if success:
            return "Webhook সফলভাবে ডিলিট করা হয়েছে!", 200
        else:
            return "Webhook ডিলিট করতে ব্যর্থ!", 500
    except RuntimeError as e:
        logger.error(f"Webhook ডিলিট করতে RuntimeError: {e}")
        try:
            if ptb_application and hasattr(ptb_application, 'loop') and ptb_application.loop.is_running():
                 future = asyncio.run_coroutine_threadsafe(_delete_webhook_async(), ptb_application.loop)
                 success = future.result(timeout=10)
                 if success:
                     return f"Webhook সফলভাবে ডিলিট করা হয়েছে (থ্রেডসেফ)!", 200
                 else:
                     return "Webhook ডিলিট করতে ব্যর্থ (থ্রেডসেফ)!", 500
            else:
                 logger.warning("PTB application loop is not available or not running for threadsafe delete.")
                 return f"Webhook ডিলিট করতে সমস্যা: {e} (PTB loop unavailable for threadsafe)", 500
        except Exception as ex_inner:
            logger.error(f"Webhook ডিলিট করতে থ্রেডসেফ পদ্ধতিতে সমস্যা: {ex_inner}")
            return f"Webhook ডিলিট করতে সমস্যা (থ্রেডসেফ): {ex_inner}", 500
    except Exception as e:
        logger.error(f"Webhook ডিলিট করতে সাধারণ সমস্যা: {e}")
        return f"Webhook ডিলিট করতে সাধারণ সমস্যা: {e}", 500

# রুট পেজ (অপশনাল, শুধু বট চলছে কিনা বোঝার জন্য)
@app.route('/')
def index():
    if ptb_application is None:
        return "Telegram Bot is NOT running (BOT_TOKEN missing or invalid).", 500
    return "Telegram Bot is running with Flask!", 200

def main() -> None:
    """বট চালু করে"""
    if not ptb_application:
        logger.critical("Telegram Application বিল্ড করা যায়নি। BOT_TOKEN চেক করুন।")
        return

    # হ্যান্ডলার যোগ করা
    ptb_application.add_handler(CommandHandler("start", start_command))
    ptb_application.add_handler(CallbackQueryHandler(button_callback_handler))
    logger.info("Bot handlers are set up.")

if ptb_application: 
    main()