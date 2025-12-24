import ccxt
import os
import time
import requests
import pandas as pd
import numpy as np
from datetime import datetime

# ================== CONFIG ==================
SYMBOLS = [
    "BTC/USDT:USDT",
    "ETH/USDT:USDT",
    "SOL/USDT:USDT",
    "BNB/USDT:USDT",
    "XRP/USDT:USDT",
    "ADA/USDT:USDT",
    "AVAX/USDT:USDT",
    "DOGE/USDT:USDT",
]

RISK_PERCENT = 0.30        # 30% of free margin
STOP_LOSS_PCT = 0.007     # 0.7%
TAKE_PROFIT_PCT = 0.015   # 1.5%
LEVERAGE = 3

CHECK_INTERVAL = 15       # seconds (for SL/TP monitor)

# ============================================

def send_telegram(msg):
    token = os.getenv("telegram_token")
    chat_id = os.getenv("chat_id")
    if not token or not chat_id:
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    requests.post(url, data={"chat_id": chat_id, "text": msg})

exchange = ccxt.coinex({
    "apiKey": os.getenv("COINEX_API_KEY"),
    "secret": os.getenv("COINEX_API_SECRET"),
    "enableRateLimit": True,
    "options": {"defaultType": "swap"},
})

exchange.load_markets()

# ================== INDICATORS ==================
def EMA(series, period):
    return series.ewm(span=period).mean()

def RSI(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    rs = gain.rolling(period).mean() / loss.rolling(period).mean()
    return 100 - (100 / (1 + rs))

def signal_strength(symbol):
    try:
        ohlcv_15m = exchange.fetch_ohlcv(symbol, "15m", limit=100)
        ohlcv_1h = exchange.fetch_ohlcv(symbol, "1h", limit=100)

        df15 = pd.DataFrame(ohlcv_15m, columns=["t","o","h","l","c","v"])
        df1h = pd.DataFrame(ohlcv_1h, columns=["t","o","h","l","c","v"])

        df15["ema_fast"] = EMA(df15["c"], 20)
        df15["ema_slow"] = EMA(df15["c"], 50)
        df15["rsi"] = RSI(df15["c"])

        df1h["ema_fast"] = EMA(df1h["c"], 20)
        df1h["ema_slow"] = EMA(df1h["c"], 50)

        trend_1h = df1h["ema_fast"].iloc[-1] > df1h["ema_slow"].iloc[-1]
        cross_15m = df15["ema_fast"].iloc[-1] > df15["ema_slow"].iloc[-1]
        rsi = df15["rsi"].iloc[-1]

        strength = 0
        side = None

        if trend_1h and cross_15m and rsi > 55:
            strength = abs(rsi - 50)
            side = "LONG"

        if (not trend_1h) and (not cross_15m) and rsi < 45:
            strength = abs(50 - rsi)
            side = "SHORT"

        return strength, side

    except:
        return 0, None

# ================== SELECT BEST ==================
best = {"symbol": None, "strength": 0, "side": None}

for sym in SYMBOLS:
    strength, side = signal_strength(sym)
    if side and strength > best["strength"]:
        best = {"symbol": sym, "strength": strength, "side": side}

if not best["symbol"]:
    send_telegram("🚀 Auto Futures Bot Started\n\n❌ No strong signal found")
    exit()

symbol = best["symbol"]
side = best["side"]

# ================== POSITION SIZE ==================
balance = exchange.fetch_balance()
free_usdt = balance["USDT"]["free"]
margin = free_usdt * RISK_PERCENT
ticker = exchange.fetch_ticker(symbol)
price = ticker["last"]

amount = (margin * LEVERAGE) / price
amount = float(exchange.amount_to_precision(symbol, amount))

# ================== OPEN ORDER ==================
send_telegram("🚀 Auto Futures Bot Started")

order = exchange.create_order(
    symbol=symbol,
    type="market",
    side="buy" if side == "LONG" else "sell",
    amount=amount
)

entry = price
sl = entry * (1 - STOP_LOSS_PCT) if side == "LONG" else entry * (1 + STOP_LOSS_PCT)
tp = entry * (1 + TAKE_PROFIT_PCT) if side == "LONG" else entry * (1 - TAKE_PROFIT_PCT)

send_telegram(
    f"✅ TRADE OPENED\n\n"
    f"Symbol: {symbol}\n"
    f"Side: {side}\n"
    f"Entry: {entry:.4f}\n"
    f"Amount: {amount}\n"
    f"SL: {sl:.4f}\n"
    f"TP: {tp:.4f}"
)

# ================== MONITOR SL / TP ==================
while True:
    price = exchange.fetch_ticker(symbol)["last"]

    if side == "LONG" and (price <= sl or price >= tp):
        exchange.create_order(symbol, "market", "sell", amount)
        result = "TP HIT ✅" if price >= tp else "SL HIT ❌"
        break

    if side == "SHORT" and (price >= sl or price <= tp):
        exchange.create_order(symbol, "market", "buy", amount)
        result = "TP HIT ✅" if price <= tp else "SL HIT ❌"
        break

    time.sleep(CHECK_INTERVAL)

send_telegram(
    f"⏹ POSITION CLOSED\n\n"
    f"{result}\n"
    f"Exit Price: {price:.4f}"
)
