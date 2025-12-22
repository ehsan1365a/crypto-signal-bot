import os
import requests
import ccxt
import pandas as pd
import ta
from datetime import datetime

# ===== DEBUG ENV =====
print("ENV telegram_token =", os.getenv("telegram_token"))
print("ENV chat_id =", os.getenv("chat_id"))

TELEGRAM_TOKEN = os.getenv("telegram_token")
CHAT_ID = os.getenv("chat_id")

def send(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    r = requests.post(url, json={
        "chat_id": CHAT_ID,
        "text": msg
    })
    print("Telegram status:", r.status_code)
    print("Telegram response:", r.text)

# ===== TEST MESSAGE =====
send("✅ TEST MESSAGE: GitHub Actions connected")

# ===== STOP HERE FOR DEBUG =====
# اگر این پیام نیومد، مشکل فقط تلگرام/سکرت‌هاست

SYMBOLS = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
TIMEFRAMES = ["15m"]

exchange = ccxt.coinex({"enableRateLimit": True})

for symbol in SYMBOLS:
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe="15m", limit=100)
    df = pd.DataFrame(ohlcv, columns=["t","o","h","l","c","v"])
    df["ema50"] = ta.trend.EMAIndicator(df["c"], 50).ema_indicator()
    df["ema200"] = ta.trend.EMAIndicator(df["c"], 200).ema_indicator()

    last = df.iloc[-1]

    if last["ema50"] > last["ema200"]:
        send(f"🟢 {symbol} BULLISH")
