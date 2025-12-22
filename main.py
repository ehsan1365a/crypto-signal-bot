import ccxt
import os
import time
import requests
import pandas as pd
from datetime import datetime

# =======================
# CONFIG
# =======================
SYMBOL = "ETH/USDT"
TIMEFRAME = "15m"
LEVERAGE = 5
POSITION_USDT = 8   # سرمایه هر معامله (دلار)

ATR_PERIOD = 14
ATR_SL = 1.5
ATR_TP = 3.0

# =======================
# TELEGRAM
# =======================
TELEGRAM_TOKEN = os.getenv("telegram_token")
CHAT_ID = os.getenv("chat_id")

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": msg}
    requests.post(url, data=data)

# =======================
# EXCHANGE (COINEX FUTURES)
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
# INDICATORS
# =======================
def get_atr(df, period=14):
    high = df["high"]
    low = df["low"]
    close = df["close"]

    tr = pd.concat([
        high - low,
        abs(high - close.shift()),
        abs(low - close.shift())
    ], axis=1).max(axis=1)

    return tr.rolling(period).mean()

# =======================
# MAIN LOGIC
# =======================
def run_bot():
    try:
        ohlcv = exchange.fetch_ohlcv(SYMBOL, TIMEFRAME, limit=100)
        df = pd.DataFrame(ohlcv, columns=["time","open","high","low","close","vol"])
        price = df["close"].iloc[-1]

        atr = get_atr(df, ATR_PERIOD).iloc[-1]

        # ساده‌ترین استراتژی جهت‌دار
        side = "LONG" if df["close"].iloc[-1] > df["close"].iloc[-2] else "SHORT"

        sl = price - ATR_SL * atr if side == "LONG" else price + ATR_SL * atr
        tp = price + ATR_TP * atr if side == "LONG" else price - ATR_TP * atr

        # =======================
        # OPEN ORDER
        # =======================
        if side == "LONG":
            order = exchange.create_market_buy_order(SYMBOL, POSITION_USDT)
        else:
            contracts = (POSITION_USDT * LEVERAGE) / price
            order = exchange.create_market_sell_order(SYMBOL, contracts)

        msg = f"""
📡 Futures Trade Bot (ATR-Based)
Time: {datetime.now()}

🟢 {SYMBOL}
Side: {side}
Entry: {price:.4f}
SL: {sl:.4f}
TP: {tp:.4f}
Size: ${POSITION_USDT}
"""
        send_telegram(msg)

    except Exception as e:
        send_telegram(f"❌ Order error: {str(e)}")

# =======================
# RUN
# =======================
run_bot()
