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
            return (
                set(data.get("users", [])),
                set(data.get("left", [])),
                set(data.get("admins", [ADMIN_ID])),
                data.get("channels", [])
            )
    return set(), set(), {ADMIN_ID}, []

def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "users": list(user_db),
            "left": list(left_users),
            "admins": list(ADMINS),
            "channels": required_channels
        }, f, ensure_ascii=False, indent=2)

# 📥 Ma'lumotlarni yuklash
user_db, left_users, ADMINS, required_channels = load_data()

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
        buttons = [[InlineKeyboardButton(f"📢 {ch}", url=f"https://t.me/{ch.lstrip('@')}")] for ch in not_subscribed]
        buttons.append([InlineKeyboardButton("✅ Tekshirish", callback_data="check_subs")])
        reply_markup = InlineKeyboardMarkup(buttons)
        await update.message.reply_text("‼️ O‘yinni boshlashdan oldin quyidagi kanallarga obuna bo‘ling:", reply_markup=reply_markup)
        return

    game_button = InlineKeyboardButton("🎮 Join Game", web_app=WebAppInfo(url="https://coin-ton-6pu6.vercel.app/"))
    await update.message.reply_text("✅ Obuna tasdiqlandi. O‘yinni boshlang!", reply_markup=InlineKeyboardMarkup([[game_button]]))

# /admin komandasi
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        await update.message.reply_text("⛔ Bu bo‘lim faqat adminlar uchun.")
        return

    keyboard = ReplyKeyboardMarkup([
        ["📊 Statistika", "📋 Ro‘yxat"],
        ["➕ Obuna qo‘shish", "➖ Obunani o‘chirish"],
        ["📤 Xabar yuborish", "👤 Admin qo‘shish"],
        ["🗂 Adminlar", "⬅️ Ortga"]
    ], resize_keyboard=True)

    await update.message.reply_text("Admin menyusi:", reply_markup=keyboard)

# Admin matnli xabarlarni boshqarish
async def handle_admin_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text.strip()

    if user.id not in ADMINS:
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
        await update.message.reply_text(f"📨 Xabar yuborildi:\n✅ Yuborildi: {success} ta\n❌ Xato: {failed} ta")
        return

    if text == "📊 Statistika":
        await update.message.reply_text(f"👥 Faol foydalanuvchilar: {len(user_db)}\n🚫 Chiqqanlar: {len(left_users)}")
    elif text == "📋 Ro‘yxat":
        msg = "\n".join(required_channels) if required_channels else "📭 Kanal ro'yxati bo'sh."
        await update.message.reply_text(msg)
    elif text == "➕ Obuna qo‘shish":
        context.user_data["adding_channel"] = True
        await update.message.reply_text("🔗 Kanal userini yuboring (masalan: @kanal):")
    elif text == "➖ Obunani o‘chirish":
        if not required_channels:
            await update.message.reply_text("📭 Kanal yo'q.")
            return
        buttons = [[InlineKeyboardButton(f"❌ {ch}", callback_data=f"remove_{i}")] for i, ch in enumerate(required_channels)]
        await update.message.reply_text("O'chirmoqchi bo'lgan kanalni tanlang:", reply_markup=InlineKeyboardMarkup(buttons))
    elif text == "📤 Xabar yuborish":
        context.user_data["awaiting_broadcast"] = True
        await update.message.reply_text("✉️ Xabaringizni yuboring (matn, media, stiker...)")
    elif text == "👤 Admin qo‘shish":
        if user.id != ADMIN_ID:
            await update.message.reply_text("⛔ Sizda ruxsat yo‘q.")
            return
        context.user_data["adding_admin"] = True
        await update.message.reply_text("🆔 Yangi admin ID raqamini yuboring:")
    elif text == "🗂 Adminlar":
        buttons = [
            [InlineKeyboardButton(f"👤 {aid}", callback_data=f"select_admin_{aid}")]
            for aid in ADMINS
        ]
        await update.message.reply_text("🧾 Adminlar ro‘yxati:", reply_markup=InlineKeyboardMarkup(buttons))
    elif text == "⬅️ Ortga":
        await start(update, context)
    elif context.user_data.get("adding_channel"):
        if text.startswith("@"):
            required_channels.append(text)
            save_data()
            await update.message.reply_text(f"✅ Qo‘shildi: {text}")
        else:
            await update.message.reply_text("❌ Noto‘g‘ri format. @ bilan yozing.")
        context.user_data["adding_channel"] = False
    elif context.user_data.get("adding_admin"):
        try:
            new_admin = int(text)
            if new_admin not in ADMINS:
                ADMINS.add(new_admin)
                save_data()
                await update.message.reply_text(f"✅ Yangi admin qo‘shildi: {new_admin}")
            else:
                await update.message.reply_text("✅ Bu foydalanuvchi allaqachon admin.")
        except:
            await update.message.reply_text("❌ Noto‘g‘ri ID raqam.")
        context.user_data["adding_admin"] = False

# Callback handler
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if query.data.startswith("remove_") and user_id in ADMINS:
        index = int(query.data.split("_")[1])
        if 0 <= index < len(required_channels):
            removed = required_channels.pop(index)
            save_data()
            await query.edit_message_text(f"❌ Kanal o‘chirildi: {removed}")
        else:
            await query.edit_message_text("⚠️ Xatolik yuz berdi.")

    elif query.data.startswith("select_admin_"):
        selected_admin = int(query.data.split("_")[2])
        if user_id != ADMIN_ID:
            await query.edit_message_text("⛔ Faqat asosiy admin o‘chira oladi.")
            return
        if selected_admin == ADMIN_ID:
            await query.edit_message_text("❗ O‘zingizni o‘chira olmaysiz.")
            return
        button = [[InlineKeyboardButton("🗑 O‘chirish", callback_data=f"removeadmin_{selected_admin}")]]
        await query.edit_message_text(f"🧾 Tanlangan admin ID: {selected_admin}", reply_markup=InlineKeyboardMarkup(button))

    elif query.data.startswith("removeadmin_"):
        remove_id = int(query.data.split("_")[1])
        if user_id == ADMIN_ID and remove_id in ADMINS and remove_id != ADMIN_ID:
            ADMINS.remove(remove_id)
            save_data()
            await query.edit_message_text(f"✅ Admin o‘chirildi: {remove_id}")
        else:
            await query.edit_message_text("❌ O‘chirish mumkin emas.")

    elif query.data == "check_subs":
        not_subscribed = []
        for ch in required_channels:
            try:
                member = await context.bot.get_chat_member(chat_id=ch, user_id=user_id)
                if member.status not in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
                    not_subscribed.append(ch)
            except:
                not_subscribed.append(ch)

        if not_subscribed:
            buttons = [[InlineKeyboardButton(f"📢 {ch}", url=f"https://t.me/{ch.lstrip('@')}")] for ch in not_subscribed]
            buttons.append([InlineKeyboardButton("✅ Qayta tekshirish", callback_data="check_subs")])
            await query.edit_message_text("🚫 Siz hali ham barcha kanallarga obuna bo‘lmagansiz:", reply_markup=InlineKeyboardMarkup(buttons))
        else:
            game_button = InlineKeyboardButton("🎮 Join Game", web_app=WebAppInfo(url="https://coin-ton-6pu6.vercel.app/"))
            await query.edit_message_text("✅ Obuna tekshirildi. O‘yinga kirishingiz mumkin!", reply_markup=InlineKeyboardMarkup([[game_button]]))

# RUN
if __name__ == "__main__":
    import asyncio

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_admin_text))
    app.add_handler(CallbackQueryHandler(handle_callback))

    print("Bot ishga tushdi!")
    asyncio.run(app.run_polling())
