import os
import logging
from flask import Flask, request, abort
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler
from dotenv import load_dotenv # শুধু লোকাল ডেভেলপমেন্টের জন্য

# --- কনফিগারেশন শুরু ---
# .env ফাইল থেকে ভ্যারিয়েবল লোড করবে (যদি থাকে, Render-এ এটি লাগবে না)
load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
WEB_APP_URL = os.getenv('WEB_APP_URL') # আপনার ওয়েবসাইটের URL
# Render অ্যাপের URL (Webhook সেট করার জন্য, Render স্বয়ংক্রিয়ভাবে এটি দেয় না, তাই নিজে সেট করতে হবে)
# অথবা, Render ড্যাশবোর্ড থেকে ডেপ্লয়মেন্টের পর URL টি নিয়ে Webhook সেট করতে হবে।
# আপাতত, আমরা Webhook সেটআপের জন্য একটি আলাদা রুট রাখবো।
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
    # প্রডাকশনে এখানে এক্সিট করা উচিত অথবা অন্যভাবে হ্যান্ডেল করা উচিত
    # আপাতত লোকাল ডেভেলপমেন্টের জন্য None দিয়ে রাখছি যাতে ইম্পোর্ট হয়
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
        return False # কোনো এরর হলে ধরে নিচ্ছি জয়েন করেনি (নিরাপত্তার জন্য)

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
    await query.answer() # কলব্যাকের উত্তর পাঠানো জরুরি

    if query.data == 'check_join_status':
        # ব্যবহারকারী "আমি জয়েন করেছি" বাটনে ক্লিক করলে, /start কমান্ডের লজিক আবার চালানো হবে
        # একটি নতুন মেসেজ হিসেবে স্ট্যাটাস দেখানো ভালো, আগের মেসেজ এডিট করার চেয়ে
        # তাই আমরা স্টার্ট কমান্ডের লজিকটাকেই কল করব, তবে একটি নতুন মেসেজ হিসেবে।
        # এর জন্য, আমরা একটি ডামি মেসেজ অবজেক্ট তৈরি করতে পারি অথবা শুধু ফাংশন কল করতে পারি।
        # সরাসরি start_command কল করার জন্য update.message লাগবে, যা callback query তে থাকে না।
        # তাই আমরা স্ট্যাটাস মেসেজ নতুন করে পাঠাবো।

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
            # আগের মেসেজ ডিলিট করে নতুন মেসেজ পাঠানো যেতে পারে, অথবা শুধু নতুন মেসেজ
            # await query.message.delete() # আগের জয়েন মেসেজ ডিলিট করতে চাইলে
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
            # আগের মেসেজ এডিট করা যেতে পারে
            try:
                await query.edit_message_text(text=join_message, reply_markup=reply_markup, parse_mode='HTML')
            except Exception as e: # যদি মেসেজ খুব পুরোনো হয় বা কনটেন্ট একই থাকে, এডিট ফেইল হতে পারে
                logger.error(f"Could not edit message: {e}")
                # নতুন মেসেজ পাঠানো ফলব্যাক হিসেবে
                await context.bot.send_message(chat_id=chat_id, text=join_message, reply_markup=reply_markup, parse_mode='HTML')


# Flask রুট: Webhook রিসিভ করার জন্য
@app.route('/webhook', methods=['POST'])
async def webhook():
    if request.method == "POST":
        json_data = request.get_json()
        if not json_data:
            logger.warning("Received empty JSON data.")
            abort(400)
        
        update = Update.de_json(json_data, ptb_application.bot)
        logger.info(f"Received update: {update.update_id}")
        await ptb_application.process_update(update)
        return '', 200 # টেলিগ্রামকে জানাতে যে আপডেট রিসিভ হয়েছে
    else:
        abort(400)

# Flask রুট: Webhook সেট করার জন্য (শুধু একবার রান করতে হবে)
@app.route('/set_webhook', methods=['GET'])
async def set_webhook():
    if not RENDER_APP_URL:
        return "RENDER_APP_URL এনভায়রনমেন্ট ভ্যারিয়েবল সেট করা নেই!", 500
    
    webhook_url = f"{RENDER_APP_URL}/webhook" # নিশ্চিত করুন আপনার RENDER_APP_URL এ ট্রেইলিং স্ল্যাশ নেই
    
    try:
        success = await ptb_application.bot.set_webhook(url=webhook_url)
        if success:
            return f"Webhook সফলভাবে সেট করা হয়েছে: {webhook_url}", 200
        else:
            return "Webhook সেট করতে ব্যর্থ!", 500
    except Exception as e:
        logger.error(f"Webhook সেট করতে সমস্যা: {e}")
        return f"Webhook সেট করতে সমস্যা: {e}", 500

@app.route('/delete_webhook', methods=['GET'])
async def delete_webhook_route():
    try:
        success = await ptb_application.bot.delete_webhook()
        if success:
            return "Webhook সফলভাবে ডিলিট করা হয়েছে!", 200
        else:
            return "Webhook ডিলিট করতে ব্যর্থ!", 500
    except Exception as e:
        logger.error(f"Webhook ডিলিট করতে সমস্যা: {e}")
        return f"Webhook ডিলিট করতে সমস্যা: {e}", 500

# রুট পেজ (অপশনাল, শুধু বট চলছে কিনা বোঝার জন্য)
@app.route('/')
def index():
    return "Telegram Bot is running with Flask!", 200

def main() -> None:
    """বট চালু করে"""
    if not ptb_application:
        logger.critical("Telegram Application বিল্ড করা যায়নি। BOT_TOKEN চেক করুন।")
        return

    # হ্যান্ডলার যোগ করা
    ptb_application.add_handler(CommandHandler("start", start_command))
    ptb_application.add_handler(CallbackQueryHandler(button_callback_handler))

    # লোকাল ডেভেলপমেন্টের জন্য (Render gunicorn ব্যবহার করবে)
    # Flask অ্যাপটি একটি ভিন্ন থ্রেডে বা প্রসেসে চলতে পারে,
    # কিন্তু python-telegram-bot v20+ asyncio ব্যবহার করে,
    # তাই gunicorn এর সাথে কিভাবে ইন্টিগ্রেট করতে হবে তা দেখতে হবে।
    # সাধারণত gunicorn নিজেই worker তৈরি করে।

    # এই main() ফাংশনটি Render gunicorn দিয়ে চালালে সরাসরি কল হবে না।
    # gunicorn app:app কমান্ড দিলে Flask অ্যাপ অবজেক্ট 'app' কে লোড করবে।
    # Webhook এর মাধ্যমে বট চলবে।
    logger.info("Bot handlers are set up.")

if ptb_application: # শুধুমাত্র যদি অ্যাপ্লিকেশন সফলভাবে তৈরি হয়
    main() # হ্যান্ডলারগুলো সেট করার জন্য main() কল করা হচ্ছে

# Gunicorn এই 'app' অবজেক্টটি খুঁজবে
# Flask অ্যাপটি রান করার জন্য, gunicorn কমান্ড টার্মিনালে দিতে হবে:
# gunicorn app:app
# Render-এ Start Command হিসেবে এটি ব্যবহার করা হবে।