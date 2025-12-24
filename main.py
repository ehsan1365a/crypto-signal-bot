import ccxt
import pandas as pd
import ta
import os
import requests
from datetime import datetime

# ===== CONFIG =====
SYMBOLS = ["BTC/USDT:USDT", "ETH/USDT:USDT", "XRP/USDT:USDT"]
LEVERAGE = 3
MARGIN_USDT = 6
TIMEFRAME_TREND = "1h"
TIMEFRAME_ENTRY = "15m"

# ===== TELEGRAM =====
def send_telegram(msg):
    url = f"https://api.telegram.org/bot{os.getenv('TELEGRAM_TOKEN')}/sendMessage"
    requests.post(url, json={"chat_id": os.getenv("CHAT_ID"), "text": msg})

send_telegram("🚀 Auto Futures Bot Started")

# ===== EXCHANGE =====
exchange = ccxt.coinex({
    "apiKey": os.getenv("COINEX_API_KEY"),
    "secret": os.getenv("COINEX_API_SECRET"),
    "options": {"defaultType": "swap"}
})

best_signal = None
best_score = 0

for symbol in SYMBOLS:
    try:
        # ===== TREND (1H) =====
        ohlc1 = exchange.fetch_ohlcv(symbol, TIMEFRAME_TREND, limit=200)
        df1 = pd.DataFrame(ohlc1, columns=["t","o","h","l","c","v"])
        df1["ema100"] = ta.trend.EMAIndicator(df1["c"], 100).ema_indicator()
        trend = "LONG" if df1["c"].iloc[-1] > df1["ema100"].iloc[-1] else "SHORT"

        # ===== ENTRY (15M) =====
        ohlc2 = exchange.fetch_ohlcv(symbol, TIMEFRAME_ENTRY, limit=200)
        df2 = pd.DataFrame(ohlc2, columns=["t","o","h","l","c","v"])

        df2["rsi"] = ta.momentum.RSIIndicator(df2["c"], 14).rsi()
        df2["atr"] = ta.volatility.AverageTrueRange(
            df2["h"], df2["l"], df2["c"], 14
        ).average_true_range()

        rsi = df2["rsi"].iloc[-1]
        atr = df2["atr"].iloc[-1]
        close = df2["c"].iloc[-1]

        valid = False
        if trend == "LONG" and 40 < rsi < 65:
            valid = True
        if trend == "SHORT" and 35 < rsi < 60:
            valid = True

        score = abs(50 - rsi) + atr

        if valid and score > best_score:
            best_score = score
            best_signal = {
                "symbol": symbol,
                "side": trend,
                "price": close,
                "atr": atr
            }

    except Exception as e:
        send_telegram(f"⚠️ {symbol} error: {e}")

# ===== EXECUTE BEST SIGNAL =====
if best_signal:
    symbol = best_signal["symbol"]
    side = best_signal["side"]
    price = best_signal["price"]
    atr = best_signal["atr"]

    amount = round((MARGIN_USDT * LEVERAGE) / price, 4)
    sl = price - atr if side == "LONG" else price + atr
    tp = price + atr*2 if side == "LONG" else price - atr*2

    exchange.set_leverage(LEVERAGE, symbol)

    order = exchange.create_market_order(
        symbol,
        "buy" if side == "LONG" else "sell",
        amount
    )

    exchange.create_order(symbol, "stop", "sell" if side == "LONG" else "buy", amount, sl)
    exchange.create_order(symbol, "limit", "sell" if side == "LONG" else "buy", amount, tp)

    send_telegram(
        f"✅ AUTO TRADE EXECUTED\n\n"
        f"{symbol}\n"
        f"Side: {side}\n"
        f"Entry: {price}\n"
        f"SL: {round(sl,4)}\n"
        f"TP: {round(tp,4)}\n"
        f"Leverage: {LEVERAGE}x\n"
        f"Margin: {MARGIN_USDT} USDT"
    )
else:
    send_telegram("❌ No strong signal found")

send_telegram("⏹ Bot Finished")
