# Telegram 2FA Bot with QR (via API)

✅ Features:
- Send QR code image
- Decodes using `https://api.qrserver.com/v1/read-qr-code/`
- Extracts secret from URL
- /code command returns OTP

## Deploy via Railway

- Add environment variable:
  - BOT_TOKEN = <your_bot_token>
- Set Start Command:
  - python main.py

✅ No OpenCV or zbar dependency, works cleanly on Railway!
