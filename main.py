import ccxt
import os
import requests
import time
from datetime import datetime

# =======================
# Telegram
# =======================
TELEGRAM_TOKEN = os.getenv("telegram_token")
CHAT_ID = os.getenv("chat_id")

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": msg}
    requests.post(url, data=data)

# =======================
# CoinEx Futures
# =======================
exchange = ccxt.coinex({
    "apiKey": os.getenv("COINEX_API_KEY"),
    "secret": os.getenv("COINEX_API_SECRET"),
    "enableRateLimit": True,
    "options": {
        "defaultType": "swap",
        "createMarketBuyOrderRequiresPrice": False
    }
})

# =======================
# Settings
# =======================
SYMBOLS = [
    "ADA/USDT",
    "XRP/USDT",
    "DOGE/USDT"
]

TIMEFRAME = "15m"
USDT_PER_TRADE = 6
LEVERAGE = 3

# =======================
# Functions
# =======================
def set_leverage(symbol):
    try:
        exchange.set_leverage(LEVERAGE, symbol)
    except:
        pass

def get_signal(symbol):
    candles = exchange.fetch_ohlcv(symbol, TIMEFRAME, limit=20)
    closes = [c[4] for c in candles]

    fast_ma = sum(closes[-5:]) / 5
    slow_ma = sum(closes[-15:]) / 15

    price = closes[-1]

    if fast_ma > slow_ma:
        return "LONG", price
    elif fast_ma < slow_ma:
        return "SHORT", price
    else:
        return None, price

def open_trade(symbol, side, price):
    set_leverage(symbol)

    amount = (USDT_PER_TRADE * LEVERAGE) / price
    amount = float(exchange.amount_to_precision(symbol, amount))

    try:
        order = exchange.create_order(
            symbol=symbol,
            type="market",
            side="buy" if side == "LONG" else "sell",
            amount=amount
        )

        send_telegram(
            f"✅ Trade Opened\n"
            f"{symbol}\n"
            f"Side: {side}\n"
            f"Price: {price}\n"
            f"Size: {USDT_PER_TRADE}$\n"
            f"Time: {datetime.now()}"
        )

    except Exception as e:
        send_telegram(f"❌ Order error: {str(e)}")

# =======================
# Run Bot
# =======================
send_telegram("🚀 Futures Bot Started")

for symbol in SYMBOLS:
    try:
        side, price = get_signal(symbol)

        if side:
            open_trade(symbol, side, price)
            break  # فقط یک معامله باز شود

    except Exception as e:
        send_telegram(f"⚠️ Error {symbol}: {str(e)}")

send_telegram("⏹ Bot Finished")
