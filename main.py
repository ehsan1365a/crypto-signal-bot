import ccxt
import os
import requests
from datetime import datetime

# ===== CONFIG =====
TELEGRAM_TOKEN = os.getenv("telegram_token")
CHAT_ID = os.getenv("chat_id")

# اتصال به CoinEx با API Key و Secret
exchange = ccxt.coinex({
    "enableRateLimit": True,
    "apiKey": os.getenv("COINEX_API_KEY"),
    "secret": os.getenv("COINEX_API_SECRET")
})

# تابع ارسال پیام تلگرام
def send(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    r = requests.post(url, json={"chat_id": CHAT_ID, "text": msg})
    print("Telegram status:", r.status_code, "| Response:", r.text)

# تست اتصال به API
try:
    balance = exchange.fetch_balance()
    send(f"✅ API Key works! USDT Balance: {balance['total'].get('USDT', 0)}")
except Exception as e:
    send(f"❌ API Key problem: {e}")
