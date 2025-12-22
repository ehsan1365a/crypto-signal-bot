import ccxt
import os
import requests
import pandas as pd
from datetime import datetime

# =======================
# CONFIG
# =======================
SYMBOLS = ["ETH/USDT", "SOL/USDT", "BNB/USDT", "BTC/USDT", "ADA/USDT"]
TIMEFRAME = "15m"
LEVERAGE = 3
POSITION_USDT = 18   # سرمایه هر معامله

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
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

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
# INDICATOR
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
# SIGNAL STRENGTH CALCULATION
# =======================
def signal_strength(df, atr):
    # ساده‌ترین معیار: فاصله close از close قبلی نسبت به ATR
    diff = abs(df["close"].iloc[-1] - df["close"].iloc[-2])
    return diff / atr if atr != 0 else 0

# =======================
# MAIN LOGIC
# =======================
def run_bot():
    signals = []

    for SYMBOL in SYMBOLS:
        try:
            ohlcv = exchange.fetch_ohlcv(SYMBOL, TIMEFRAME, limit=100)
            df = pd.DataFrame(ohlcv, columns=["time","open","high","low","close","vol"])
            price = df["close"].iloc[-1]
            atr = get_atr(df, ATR_PERIOD).iloc[-1]

            side = "LONG" if df["close"].iloc[-1] > df["close"].iloc[-2] else "SHORT"
            strength = signal_strength(df, atr)

            signals.append({
                "symbol": SYMBOL,
                "side": side,
                "price": price,
                "atr": atr,
                "strength": strength
            })

        except Exception as e:
            send_telegram(f"❌ Error fetching {SYMBOL}: {e}")

    # انتخاب قوی‌ترین سیگنال
    if not signals:
        send_telegram("❌ هیچ سیگنالی پیدا نشد")
        return

    best_signal = max(signals, key=lambda x: x["strength"])
    symbol = best_signal["symbol"]
    side = best_signal["side"]
    price = best_signal["price"]
    atr = best_signal["atr"]

    sl = price - ATR_SL * atr if side == "LONG" else price + ATR_SL * atr
    tp = price + ATR_TP * atr if side == "LONG" else price - ATR_TP * atr

    contracts = round((POSITION_USDT * LEVERAGE) / price, 4)

    # =======================
    # OPEN ORDER
    # =======================
    try:
        if side == "LONG":
            exchange.create_market_buy_order(symbol, contracts)
        else:
            exchange.create_market_sell_order(symbol, contracts)

        msg = f"""
📡 Futures Trade Bot (ATR-Based)
Time: {datetime.utcnow()}

{'🟢' if side=='LONG' else '🔴'} {symbol}
Side: {side}
Entry: {price:.4f}
SL: {sl:.4f}
TP: {tp:.4f}
Size: ${POSITION_USDT}
Leverage: {LEVERAGE}x
"""
        send_telegram(msg)

    except Exception as e:
        send_telegram(f"❌ Order error: {e}")

# =======================
# RUN
# =======================
run_bot()
