
import os
import re
import pyotp
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

user_secrets = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📤 Get Secret Key from QR", callback_data="get_secret")],
        [InlineKeyboardButton("📲 Get OTP from Secret Key", callback_data="get_code")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "👋 Hello! Send me a QR code image from Google Authenticator or type a Secret Key.",
        reply_markup=reply_markup
    )

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = await update.message.photo[-1].get_file()
    file_path = "qr.jpg"
    await file.download_to_drive(file_path)

    with open(file_path, "rb") as f:
        response = requests.post("https://api.qrserver.com/v1/read-qr-code/", files={"file": f})

    try:
        data = response.json()[0]["symbol"][0]["data"]
        if data:
            match = re.search(r'secret=([A-Z0-9]+)', data)
            label_match = re.search(r'otpauth://totp/([^?]+)', data)
            if match:
                secret = match.group(1)
                label = label_match.group(1) if label_match else "Unknown Account"
                user_secrets[update.effective_user.id] = secret
                message = (
                    f"✅ Secret Key detected from: *{label}*
"
                    f"🧾 Secret Key: `{secret}`"
                )
                await update.message.reply_text(message, parse_mode="Markdown")
            else:
                await update.message.reply_text("❌ No Secret Key found in QR.")
        else:
            await update.message.reply_text("❌ Could not decode QR code.")
    except:
        await update.message.reply_text("❌ Failed to decode QR.")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().upper()
    if re.fullmatch(r'[A-Z2-7]{16,}', text):
        user_secrets[update.effective_user.id] = text
        await update.message.reply_text("✅ Secret Key saved! Use button to get code.")
    else:
        await update.message.reply_text("⚠️ Invalid Secret Key format.")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "get_secret":
        await query.message.reply_text("📷 Please send me the QR code image.")
    elif query.data == "get_code":
        if user_id not in user_secrets:
            await query.message.reply_text("⚠️ No Secret Key found. Send QR or type key first.")
            return
        otp = pyotp.TOTP(user_secrets[user_id]).now()
        await query.message.reply_text(f"🔐 OTP Code: `{otp}`", parse_mode="Markdown")

BOT_TOKEN = "8042421392:AAHMz2z5EJxenhDryF3rAVmMwWN58BbSljs"
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button_handler))
app.add_handler(CommandHandler("code", button_handler))
app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

app.run_polling()
