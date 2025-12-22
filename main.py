import ccxt
import pandas as pd
import ta
import requests
import os
from datetime import datetime

# ===== CONFIG =====
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

SYMBOLS = [
    "BTC/USDT",
    "ETH/USDT",
    "SOL/USDT",
    "BNB/USDT",
    "XRP/USDT"
]

TIMEFRAMES = ["15m", "1h"]

exchange = ccxt.coinex({"enableRateLimit": True})

def send(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": msg})

def analyze(symbol, tf):
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf, limit=200)
    df = pd.DataFrame(ohlcv, columns=["t","o","h","l","c","v"])

    df["ema50"] = ta.trend.EMAIndicator(df["c"], 50).ema_indicator()
    df["ema200"] = ta.trend.EMAIndicator(df["c"], 200).ema_indicator()
    df["rsi"] = ta.momentum.RSIIndicator(df["c"], 14).rsi()
    df["atr"] = ta.volatility.AverageTrueRange(
        df["h"], df["l"], df["c"], 14
    ).average_true_range()

    macd = ta.trend.MACD(df["c"])
    df["macd_hist"] = macd.macd_diff()

    last = df.iloc[-1]
    price = last["c"]
    atr = last["atr"]

    if last["ema50"] > last["ema200"] and 40 < last["rsi"] < 65 and last["macd_hist"] > 0:
        return {
            "side": "LONG",
            "entry": price,
            "sl": price - (1.5 * atr),
            "tp": price + (3 * atr)
        }

    if last["ema50"] < last["ema200"] and 35 < last["rsi"] < 60 and last["macd_hist"] < 0:
        return {
            "side": "SHORT",
            "entry": price,
            "sl": price + (1.5 * atr),
            "tp": price - (3 * atr)
        }

    return None

messages = []

for symbol in SYMBOLS:
    votes = []
    for tf in TIMEFRAMES:
        result = analyze(symbol, tf)
        if result:
            votes.append(result)

    if votes:
        r = votes[0]
        messages.append(
            f"{'🟢' if r['side']=='LONG' else '🔴'} {symbol}\n"
            f"Side: {r['side']}\n"
            f"Entry: {r['entry']:.4f}\n"
            f"SL: {r['sl']:.4f}\n"
            f"TP: {r['tp']:.4f}\n"
        )

if messages:
    send(
        "📡 Futures Signal Bot (ATR Based)\n"
        f"TFs: {TIMEFRAMES}\n"
        f"Time: {datetime.utcnow()}\n\n" +
        "\n".join(messages)
    )
else:
    send("📭 No high-quality futures signals")
