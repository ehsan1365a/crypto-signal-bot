import ccxt
import pandas as pd
import numpy as np
import os
import requests
from datetime import datetime

# ====== CONFIG ======
SYMBOLS = ["BTC/USDT:USDT", "ETH/USDT:USDT", "SOL/USDT:USDT"]
LEVERAGE = 3
RISK_USDT = 8  # مارجین مصرفی
TIMEFRAME_TREND = "1h"
TIMEFRAME_ENTRY = "15m"

TELEGRAM_TOKEN = os.getenv("telegram_token")
CHAT_ID = os.getenv("chat_id")

# ====== TELEGRAM ======
def send(msg):
    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        json={"chat_id": CHAT_ID, "text": msg}
    )

# ====== EXCHANGE ======
exchange = ccxt.coinex({
    "apiKey": os.getenv("COINEX_API_KEY"),
    "secret": os.getenv("COINEX_API_SECRET"),
    "enableRateLimit": True,
    "options": {
        "defaultType": "swap",
        "createMarketBuyOrderRequiresPrice": False
    }
})

# ====== INDICATORS ======
def ema(series, n):
    return series.ewm(span=n).mean()

def rsi(series, n=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    rs = gain.rolling(n).mean() / loss.rolling(n).mean()
    return 100 - (100 / (1 + rs))

def atr(df, n=14):
    hl = df["high"] - df["low"]
    hc = abs(df["high"] - df["close"].shift())
    lc = abs(df["low"] - df["close"].shift())
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    return tr.rolling(n).mean()

# ====== SIGNAL CHECK ======
def analyze(symbol):
    df1h = pd.DataFrame(
        exchange.fetch_ohlcv(symbol, TIMEFRAME_TREND, limit=200),
        columns=["t","open","high","low","close","v"]
    )
    df15 = pd.DataFrame(
        exchange.fetch_ohlcv(symbol, TIMEFRAME_ENTRY, limit=200),
        columns=["t","open","high","low","close","v"]
    )

    df1h["ema50"] = ema(df1h["close"], 50)
    df1h["ema200"] = ema(df1h["close"], 200)

    trend = None
    if df1h["ema50"].iloc[-1] > df1h["ema200"].iloc[-1]:
        trend = "LONG"
    elif df1h["ema50"].iloc[-1] < df1h["ema200"].iloc[-1]:
        trend = "SHORT"
    else:
        return None

    df15["rsi"] = rsi(df15["close"])
    df15["atr"] = atr(df15)

    last = df15.iloc[-1]

    if trend == "LONG" and last["rsi"] > 55:
        score = last["rsi"]
    elif trend == "SHORT" and last["rsi"] < 45:
        score = 100 - last["rsi"]
    else:
        return None

    return {
        "symbol": symbol,
        "side": trend,
        "price": last["close"],
        "atr": last["atr"],
        "score": score
    }

# ====== RUN ======
send("🚀 Auto Futures Bot Started")

signals = []
for s in SYMBOLS:
    try:
        res = analyze(s)
        if res:
            signals.append(res)
    except:
        pass

if not signals:
    send("❌ No strong signal found")
    exit()

best = sorted(signals, key=lambda x: x["score"], reverse=True)[0]

symbol = best["symbol"]
side = best["side"]
price = best["price"]
atr_val = best["atr"]

exchange.set_leverage(LEVERAGE, symbol)

amount = round((RISK_USDT * LEVERAGE) / price, 4)

order = exchange.create_market_order(
    symbol,
    "buy" if side == "LONG" else "sell",
    amount
)

sl = price - atr_val if side == "LONG" else price + atr_val
tp = price + atr_val * 2 if side == "LONG" else price - atr_val * 2

exchange.create_order(
    symbol,
    "market",
    "sell" if side == "LONG" else "buy",
    amount,
    params={"stopPrice": sl, "reduceOnly": True}
)

exchange.create_order(
    symbol,
    "market",
    "sell" if side == "LONG" else "buy",
    amount,
    params={"stopPrice": tp, "reduceOnly": True}
)

send(
    f"✅ AUTO TRADE EXECUTED\n\n"
    f"{symbol}\n"
    f"Side: {side}\n"
    f"Entry: {price}\n"
    f"SL: {sl}\n"
    f"TP: {tp}\n"
    f"Amount: {amount}"
)

send("⏹ Bot Finished")
