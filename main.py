import ccxt
import pandas as pd
import ta
import requests
import os
from datetime import datetime

# ===== CONFIG =====
TELEGRAM_TOKEN = os.getenv("telegram_token")
CHAT_ID = os.getenv("chat_id")

# سرمایه هر معامله
POSITION_SIZE = 10  # دلار

SYMBOLS = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT"]
TIMEFRAMES = ["15m", "1h"]

exchange = ccxt.coinex({
    "enableRateLimit": True,
    "apiKey": os.getenv("COINEX_API_KEY"),
    "secret": os.getenv("COINEX_API_SECRET")
})

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

    score = 0
    side = None

    # امتیازدهی ساده
    if last["ema50"] > last["ema200"]:
        score += 1
    else:
        score -= 1

    if 40 < last["rsi"] < 65:
        score += 1
    elif 35 < last["rsi"] < 60:
        score -= 1

    if last["macd_hist"] > 0:
        score +=1
    elif last["macd_hist"] < 0:
        score -=1

    # تعیین سمت معامله
    if score >= 2:
        side = "LONG"
        return {"symbol": symbol, "side": side, "score": score, "entry": price, "sl": price - 1.5*atr, "tp": price + 3*atr}
    elif score <= -2:
        side = "SHORT"
        return {"symbol": symbol, "side": side, "score": score, "entry": price, "sl": price + 1.5*atr, "tp": price - 3*atr}
    else:
        return None

# ===== Main Loop =====
signals = []
for symbol in SYMBOLS:
    for tf in TIMEFRAMES:
        res = analyze(symbol, tf)
        if res:
            signals.append(res)

# انتخاب قوی‌ترین سیگنال
if signals:
    best_signal = max(signals, key=lambda x: x["score"])
    
    side = best_signal["side"]
    symbol = best_signal["symbol"]
    entry = best_signal["entry"]
    sl = best_signal["sl"]
    tp = best_signal["tp"]

    # ⚡ اصلاح Market Buy/Sell برای CoinEx
    try:
        if side == "LONG":
            exchange.create_market_buy_order(symbol, POSITION_SIZE, {'createMarketBuyOrderRequiresPrice': False})
        else:
            exchange.create_market_sell_order(symbol, POSITION_SIZE, {'createMarketBuyOrderRequiresPrice': False})
    except Exception as e:
        send(f"❌ Error opening order: {e}")

    # پیام تلگرام
    msg = f"📡 Futures Trade Bot (ATR-Based)\nTime: {datetime.utcnow()}\n\n"
    msg += f"{'🟢' if side=='LONG' else '🔴'} {symbol}\nSide: {side}\nEntry: {entry:.4f}\nSL: {sl:.4f}\nTP: {tp:.4f}\nSize: ${POSITION_SIZE}"
    send(msg)
else:
    send("📭 No strong signals on selected pairs")
