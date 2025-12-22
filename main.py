import ccxt
import pandas as pd
import ta
import requests
import os
from datetime import datetime

# ===== CONFIG =====
TELEGRAM_TOKEN = os.getenv("telegram_token")
CHAT_ID = os.getenv("chat_id")

SYMBOLS = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT"]
TIMEFRAMES = ["15m", "1h"]

exchange = ccxt.coinex({"enableRateLimit": True})

def send(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    r = requests.post(url, json={"chat_id": CHAT_ID, "text": msg})
    print("Telegram status:", r.status_code, "| Response:", r.text)

def analyze(symbol, tf):
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf, limit=200)
    df = pd.DataFrame(ohlcv, columns=["t","o","h","l","c","v"])

    # Indicators
    df["ema50"] = ta.trend.EMAIndicator(df["c"], 50).ema_indicator()
    df["ema200"] = ta.trend.EMAIndicator(df["c"], 200).ema_indicator()
    df["rsi"] = ta.momentum.RSIIndicator(df["c"], 14).rsi()
    df["atr"] = ta.volatility.AverageTrueRange(df["h"], df["l"], df["c"], 14).average_true_range()
    macd = ta.trend.MACD(df["c"])
    df["macd_hist"] = macd.macd_diff()

    last = df.iloc[-1]
    price = last["c"]
    atr = last["atr"]

    if last["ema50"] > last["ema200"] and 40 < last["rsi"] < 65 and last["macd_hist"] > 0:
        return {"side": "LONG", "entry": price, "sl": price - 1.5*atr, "tp": price + 3*atr}
    elif last["ema50"] < last["ema200"] and 35 < last["rsi"] < 60 and last["macd_hist"] < 0:
        return {"side": "SHORT", "entry": price, "sl": price + 1.5*atr, "tp": price - 3*atr}
    else:
        return None

# ===== Main Loop =====
messages = []
for symbol in SYMBOLS:
    votes = {"LONG": 0, "SHORT": 0}
    results = []
    for tf in TIMEFRAMES:
        res = analyze(symbol, tf)
        if res:
            votes[res["side"]] += 1
            results.append(res)
    # تصمیم نهایی
    if votes["LONG"] > votes["SHORT"]:
        r = results[0]
        messages.append(f"🟢 {symbol}\nSide: {r['side']}\nEntry: {r['entry']:.4f}\nSL: {r['sl']:.4f}\nTP: {r['tp']:.4f}")
    elif votes["SHORT"] > votes["LONG"]:
        r = results[0]
        messages.append(f"🔴 {symbol}\nSide: {r['side']}\nEntry: {r['entry']:.4f}\nSL: {r['sl']:.4f}\nTP: {r['tp']:.4f}")

if messages:
    msg = f"📡 Futures Signal Bot (ATR-Based)\nTFs: {TIMEFRAMES}\nTime: {datetime.utcnow()}\n\n" + "\n\n".join(messages)
    send(msg)
else:
    send("📭 No strong signals on selected pairs")
