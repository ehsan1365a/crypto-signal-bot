import ccxt
import os
import time
import pandas as pd
import numpy as np
from datetime import datetime

# =======================
# Telegram
# =======================
TELEGRAM_TOKEN = os.getenv("telegram_token")
CHAT_ID = os.getenv("chat_id")

def send_telegram(msg):
    import requests
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": msg})

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
# SETTINGS
# =======================
TIMEFRAMES = ["15m", "1h"]
RISK_USDT = 8          # مارجین
LEVERAGE = 3
ATR_MULT_SL = 1.2
ATR_MULT_TP = 2.0

SYMBOLS = [
    "BTC/USDT:USDT",
    "ETH/USDT:USDT",
    "SOL/USDT:USDT",
    "BNB/USDT:USDT",
    "XRP/USDT:USDT",
    "ADA/USDT:USDT",
    "AVAX/USDT:USDT",
    "DOGE/USDT:USDT"
]

# =======================
# Indicators
# =======================
def atr(df, period=14):
    high = df["high"]
    low = df["low"]
    close = df["close"]
    tr = np.maximum(high - low, np.maximum(abs(high - close.shift()), abs(low - close.shift())))
    return tr.rolling(period).mean()

def signal_from_tf(symbol, tf):
    ohlcv = exchange.fetch_ohlcv(symbol, tf, limit=100)
    df = pd.DataFrame(ohlcv, columns=["ts","open","high","low","close","vol"])
    df["ema_fast"] = df["close"].ewm(span=20).mean()
    df["ema_slow"] = df["close"].ewm(span=50).mean()
    df["atr"] = atr(df)

    last = df.iloc[-1]

    if last["ema_fast"] > last["ema_slow"]:
        return "LONG", last["atr"]
    elif last["ema_fast"] < last["ema_slow"]:
        return "SHORT", last["atr"]
    return None, None

# =======================
# Find Best Signal
# =======================
def find_best_signal():
    best = None

    for symbol in SYMBOLS:
        directions = []
        atrs = []

        for tf in TIMEFRAMES:
            side, atr_val = signal_from_tf(symbol, tf)
            if side:
                directions.append(side)
                atrs.append(atr_val)

        if len(directions) == len(TIMEFRAMES) and directions.count(directions[0]) == len(directions):
            strength = np.mean(atrs)
            if not best or strength > best["strength"]:
                best = {
                    "symbol": symbol,
                    "side": directions[0],
                    "atr": strength
                }

    return best

# =======================
# Execute Trade
# =======================
def execute_trade(signal):
    symbol = signal["symbol"]
    side = signal["side"]
    atr_val = signal["atr"]

    exchange.set_leverage(LEVERAGE, symbol)

    ticker = exchange.fetch_ticker(symbol)
    price = ticker["last"]

    amount = round((RISK_USDT * LEVERAGE) / price, 4)

    if side == "LONG":
        order = exchange.create_market_buy_order(symbol, amount)
        sl = price - ATR_MULT_SL * atr_val
        tp = price + ATR_MULT_TP * atr_val
        exchange.create_order(symbol, "market", "sell", amount, None, {"stopPrice": sl})
        exchange.create_order(symbol, "market", "sell", amount, None, {"stopPrice": tp})
    else:
        order = exchange.create_market_sell_order(symbol, amount)
        sl = price + ATR_MULT_SL * atr_val
        tp = price - ATR_MULT_TP * atr_val
        exchange.create_order(symbol, "market", "buy", amount, None, {"stopPrice": sl})
        exchange.create_order(symbol, "market", "buy", amount, None, {"stopPrice": tp})

    send_telegram(
        f"✅ BEST SIGNAL EXECUTED\n\n"
        f"Symbol: {symbol}\n"
        f"Side: {side}\n"
        f"Entry: {price}\n"
        f"Amount: {amount}\n"
        f"SL: {round(sl,4)}\n"
        f"TP: {round(tp,4)}"
    )

# =======================
# MAIN
# =======================
send_telegram("🚀 Auto Futures Bot Started")

try:
    signal = find_best_signal()

    if not signal:
        send_telegram("❌ No strong signal found")
    else:
        execute_trade(signal)

except Exception as e:
    send_telegram(f"❌ Bot Error: {str(e)}")

send_telegram("⏹ Bot Finished")
