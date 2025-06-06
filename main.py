import pyotp
import requests
import re
import os
import urllib.parse
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

user_secrets = {}

# ✅ Service classifier
def detect_service(label: str) -> str:
    label_lower = label.lower()
    if 'facebook' in label_lower or 'fb' in label_lower:
        return "FB 2FA"
    elif 'gmail' in label_lower or 'google' in label_lower:
        return "Gmail 2FA"
    elif 'yandex' in label_lower:
        return "Yandex 2FA"
    elif 'hotmail' in label_lower or 'outlook' in label_lower or 'microsoft' in label_lower:
        return "Hotmail 2FA"
    else:
        return "Other 2FA"

# ✅ Service buttons UI
def get_service_buttons():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🟦 FB 2FA", callback_data="fb_2fa"),
            InlineKeyboardButton("🟥 Gmail 2FA", callback_data="gmail_2fa"),
        ],
        [
            InlineKeyboardButton("🟨 Yandex 2FA", callback_data="yandex_2fa"),
            InlineKeyboardButton("🟪 Hotmail 2FA", callback_data="hotmail_2fa"),
        ]
    ])

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

                label_match = re.search(r'otpauth://totp/([^?]+)', data)
                raw_label = label_match.group(1).split(':')[-1] if label_match else "Unknown"
                label = urllib.parse.unquote(raw_label)
                service = detect_service(label)

                user_secrets[update.effective_user.id] = secret
                context.user_data['label'] = label
                context.user_data['service'] = service

                await update.message.reply_text(
                    f"✅ {service} for: *{label}*\n\n🧾 Your Key: `{secret}`",
                    parse_mode="Markdown"
                )

                await update.message.reply_text(
                    "👇 Choose a service to get OTP:",
                    reply_markup=get_service_buttons()
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
        context.user_data['service'] = "Manual 2FA"
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
        service = context.user_data.get("service", "2FA")
        if secret:
            await query.message.reply_text(
                f"✅ {service} for: *{label}*\n🧾 Your Key: `{secret}`",
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

async def handle_service_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    secret = user_secrets.get(user_id)

    if not secret:
        await query.message.reply_text("⚠️ No Secret Key found.")
        return

    otp = pyotp.TOTP(secret).now()

    if query.data == "fb_2fa":
        await query.message.reply_text(f"🔐 FB 2FA OTP: `{otp}`", parse_mode="Markdown")
    elif query.data == "gmail_2fa":
        await query.message.reply_text(f"🔐 Gmail 2FA OTP: `{otp}`", parse_mode="Markdown")
    elif query.data == "yandex_2fa":
        await query.message.reply_text(f"🔐 Yandex 2FA OTP: `{otp}`", parse_mode="Markdown")
    elif query.data == "hotmail_2fa":
        await query.message.reply_text(f"🔐 Hotmail 2FA OTP: `{otp}`", parse_mode="Markdown")

# ✅ Replace with your actual token
BOT_TOKEN = "8042421392:AAHMz2z5EJxenhDryF3rAVmMwWN58BbSljs"

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
app.add_handler(CallbackQueryHandler(handle_button, pattern="^(show_secret|show_otp)$"))
app.add_handler(CallbackQueryHandler(handle_service_buttons, pattern="^(fb_2fa|gmail_2fa|yandex_2fa|hotmail_2fa)$"))

app.run_polling()
