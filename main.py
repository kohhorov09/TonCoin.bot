from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, ReplyKeyboardMarkup
from telegram.constants import ChatMemberStatus
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler
import logging
import json
import os

# 🔐 TOKEN va ADMIN ID
BOT_TOKEN = "8145474409:AAG_DCe3s3eP8PI2jaJHXZ2CRMVQCZuxwzY"
ADMIN_ID = 7114973309

# 📁 Fayl nomi
DATA_FILE = "data.json"

# 📊 Ma'lumotlarni yuklash va saqlash funksiyalari
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return set(data.get("users", [])), set(data.get("left", []))
    return set(), set()

def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "users": list(user_db),
            "left": list(left_users)
        }, f, ensure_ascii=False, indent=2)

# 📥 Ma'lumotlarni yuklash
user_db, left_users = load_data()
required_channels = []

# 🔍 Logging
logging.basicConfig(level=logging.INFO)

# /start komandasi
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id

    if user_id not in user_db:
        user_db.add(user_id)
        save_data()

    not_subscribed = []
    for ch in required_channels:
        try:
            member = await context.bot.get_chat_member(chat_id=ch, user_id=user_id)
            if member.status not in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
                not_subscribed.append(ch)
        except:
            not_subscribed.append(ch)

    if not_subscribed:
        buttons = [
            [InlineKeyboardButton(f"📢 {ch}", url=f"https://t.me/{ch.lstrip('@')}")]
            for ch in required_channels
        ]
        buttons.append([InlineKeyboardButton("✅ Tekshirish", callback_data="check_subs")])
        reply_markup = InlineKeyboardMarkup(buttons)
        await update.message.reply_text("❗ O‘yinni boshlashdan oldin quyidagi kanallarga obuna bo‘ling:", reply_markup=reply_markup)
        return

    game_button = InlineKeyboardButton("🎮 Join Game", web_app=WebAppInfo(url="https://coin-ton.vercel.app/"))
    await update.message.reply_text("✅ Obuna tasdiqlandi. O‘yinni boshlang!", reply_markup=InlineKeyboardMarkup([[game_button]]))

# /admin komandasi
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Bu bo‘lim faqat admin uchun.")
        return

    keyboard = ReplyKeyboardMarkup([
        ["📊 Statistika", "📋 Ro‘yxat"],
        ["➕ Obuna qo‘shish", "➖ Obunani o‘chirish"],
        ["📤 Xabar yuborish"],
        ["⬅️ Ortga"]
    ], resize_keyboard=True)

    await update.message.reply_text("🔧 Admin menyusi:", reply_markup=keyboard)

# Admin handler
async def handle_admin_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text.strip()

    if user.id != ADMIN_ID:
        return

    if context.user_data.get("awaiting_broadcast"):
        success, failed = 0, 0
        message = update.message

        for uid in user_db:
            try:
                if message.text:
                    await context.bot.send_message(uid, message.text)
                elif message.photo:
                    await context.bot.send_photo(uid, photo=message.photo[-1].file_id, caption=message.caption or "")
                elif message.video:
                    await context.bot.send_video(uid, video=message.video.file_id, caption=message.caption or "")
                elif message.audio:
                    await context.bot.send_audio(uid, audio=message.audio.file_id, caption=message.caption or "")
                elif message.voice:
                    await context.bot.send_voice(uid, voice=message.voice.file_id, caption=message.caption or "")
                elif message.document:
                    await context.bot.send_document(uid, document=message.document.file_id, caption=message.caption or "")
                elif message.sticker:
                    await context.bot.send_sticker(uid, sticker=message.sticker.file_id)
                else:
                    failed += 1
                    continue
                success += 1
            except:
                left_users.add(uid)
                failed += 1
                save_data()

        context.user_data["awaiting_broadcast"] = False
        await update.message.reply_text(f"📬 Xabar yuborildi:\n✅ Yuborildi: {success} ta\n❌ Yuborilmadi: {failed} ta")
        return

    if text == "➕ Obuna qo‘shish":
        await update.message.reply_text("📩 Kanal userni yuboring (masalan: @kanal):")
        context.user_data["adding_channel"] = True
        return

    if text == "➖ Obunani o‘chirish":
        if not required_channels:
            await update.message.reply_text("📭 Hech qanday kanal mavjud emas.")
            return
        buttons = [
            [InlineKeyboardButton(f"❌ {ch}", callback_data=f"remove_{i}")]
            for i, ch in enumerate(required_channels)
        ]
        reply_markup = InlineKeyboardMarkup(buttons)
        await update.message.reply_text("O‘chirmoqchi bo‘lgan kanalni tanlang:", reply_markup=reply_markup)
        return

    if text == "📋 Ro‘yxat":
        msg = "\n".join(required_channels) if required_channels else "📭 Kanal ro‘yxati bo‘sh."
        await update.message.reply_text(msg)
        return

    if text == "📊 Statistika":
        await update.message.reply_text(
            f"👥 Umumiy foydalanuvchilar: {len(user_db)}\n🚪 Botdan chiqqanlar: {len(left_users)}"
        )
        return

    if text == "⬅️ Ortga":
        await start(update, context)
        return

    if text == "📤 Xabar yuborish":
        context.user_data["awaiting_broadcast"] = True
        await update.message.reply_text("✉️ Yubormoqchi bo‘lgan xabaringizni (matn, media, stiker...) kiriting:")
        return

    if context.user_data.get("adding_channel"):
        if text.startswith("@"):
            required_channels.append(text)
            await update.message.reply_text(f"✅ Qo‘shildi: {text}")
        else:
            await update.message.reply_text("❌ Format noto‘g‘ri. @ bilan yozing.")
        context.user_data["adding_channel"] = False

# Callback handler
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if query.data.startswith("remove_") and user_id == ADMIN_ID:
        index = int(query.data.replace("remove_", ""))
        if 0 <= index < len(required_channels):
            removed = required_channels.pop(index)
            await query.edit_message_text(f"❌ Kanal o‘chirildi: {removed}")
        else:
            await query.edit_message_text("🚫 Xatolik yuz berdi.")
        return

    if query.data == "check_subs":
        not_subscribed = []
        for ch in required_channels:
            try:
                member = await context.bot.get_chat_member(chat_id=ch, user_id=user_id)
                if member.status not in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
                    not_subscribed.append(ch)
            except:
                not_subscribed.append(ch)

        if not_subscribed:
            buttons = [
                [InlineKeyboardButton(f"📢 {ch}", url=f"https://t.me/{ch.lstrip('@')}")]
                for ch in not_subscribed
            ]
            buttons.append([InlineKeyboardButton("✅ Qayta tekshirish", callback_data="check_subs")])
            reply_markup = InlineKeyboardMarkup(buttons)
            await query.edit_message_text("🚫 Siz hali ham barcha kanallarga obuna bo‘lmagansiz:", reply_markup=reply_markup)
        else:
            game_button = InlineKeyboardButton("🎮 Join Game", web_app=WebAppInfo(url="https://coin-ton.vercel.app/"))
            await query.edit_message_text("✅ Obuna tekshirildi. O‘yinga kirishingiz mumkin!", reply_markup=InlineKeyboardMarkup([[game_button]]))

# RUN
if __name__ == "__main__":
    import asyncio

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(MessageHandler(filters.TEXT | filters.ALL & filters.User(ADMIN_ID), handle_admin_text))
    app.add_handler(CallbackQueryHandler(handle_callback))

    print("🤖 Bot ishga tushdi!")

    asyncio.get_event_loop().run_until_complete(app.run_polling())
