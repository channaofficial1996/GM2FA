import pyotp
import requests
import re
import os
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

user_secrets = {}

def get_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📤 Get Secret Key from QR", callback_data="show_secret"),
            InlineKeyboardButton("📲 Get OTP from Secret", callback_data="show_otp")
        ]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Hello! Send me a QR code image from Google Authenticator or type a Secret Key.")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = await update.message.photo[-1].get_file()
    file_path = "qr.jpg"
    await file.download_to_drive(file_path)

    with open(file_path, "rb") as f:
        response = requests.post("https://api.qrserver.com/v1/read-qr-code/", files={"file": f})

    try:
        data = response.json()[0]["symbol"][0]["data"]
        if data:
            match = re.search(r'secret=([A-Z2-7]{16,})', data, re.IGNORECASE)
            if match:
                secret = match.group(1).upper()

                # ✅ ចាប់ label/email name ពី otpauth://totp/NAME?secret=...
                label_match = re.search(r'otpauth://totp/([^?]+)', data)
                label = label_match.group(1).split(':')[-1] if label_match else "Unknown"

                user_secrets[update.effective_user.id] = secret
                context.user_data['label'] = label

                await update.message.reply_text(
                    f"✅ Secret Key detected from: *{label}*\n\n🧾 Your Key: `{secret}`",
                    parse_mode="Markdown",
                    reply_markup=get_keyboard()
                )
            else:
                await update.message.reply_text("❌ No valid Secret Key found in this QR.")
        else:
            await update.message.reply_text("❌ QR code could not be read.")
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to decode QR: {str(e)}")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().upper()
    if re.fullmatch(r'[A-Z2-7]{16,}', text):
        user_secrets[update.effective_user.id] = text
        context.user_data['label'] = "Manual Entry"
        await update.message.reply_text(
            "✅ Secret Key saved. Choose an action below:",
            reply_markup=get_keyboard()
        )
    else:
        await update.message.reply_text("⚠️ Invalid Secret Key format.")

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "show_secret":
        secret = user_secrets.get(user_id)
        label = context.user_data.get("label", "Unknown")
        if secret:
            await query.message.reply_text(
                f"Secret Key From Mail: *{label}*\n🧾 Your Key: `{secret}`",
                parse_mode="Markdown"
            )
        else:
            await query.message.reply_text("⚠️ No Secret Key found.")
    elif query.data == "show_otp":
        secret = user_secrets.get(user_id)
        if secret:
            otp = pyotp.TOTP(secret).now()
            await query.message.reply_text(f"🔐 OTP Code: `{otp}`", parse_mode="Markdown")
        else:
            await query.message.reply_text("⚠️ No Secret Key found. Please send one first.")

# ✅ Bot Token (Replace with your own)
BOT_TOKEN = "8042421392:AAHMz2z5EJxenhDryF3rAVmMwWN58BbSljs"

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
app.add_handler(CallbackQueryHandler(handle_button))

app.run_polling()
