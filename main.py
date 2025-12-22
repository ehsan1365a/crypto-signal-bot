import ccxt
import pandas as pd
import ta
import os
import requests
from datetime import datetime

# ===== CONFIG =====
TELEGRAM_TOKEN = os.getenv("telegram_token")
CHAT_ID = os.getenv("chat_id")

SYMBOLS = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT"]
TIMEFRAMES = ["15m", "1h"]

POSITION_USDT = 10      # سرمایه هر معامله
LEVERAGE = 3            # لوریج امن
MARKET_TYPE = "swap"    # Futures (USDT-M)

# ===== EXCHANGE =====
exchange = ccxt.coinex({
    "enableRateLimit": True,
    "apiKey": os.getenv("COINEX_API_KEY"),
    "secret": os.getenv("COINEX_API_SECRET"),
    "options": {
        "defaultType": MARKET_TYPE
    }
})

# ===== TELEGRAM =====
def send(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": msg})

# ===== CHECK OPEN POSITION =====
def has_open_position(symbol):
    positions = exchange.fetch_positions([symbol])
    for p in positions:
        if abs(float(p.get("contracts", 0))) > 0:
            return True
    return False

# ===== ANALYZE =====
def analyze(symbol, tf):
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf, limit=200)
    df = pd.DataFrame(ohlcv, columns=["t","o","h","l","c","v"])

    df["ema50"] = ta.trend.EMAIndicator(df["c"], 50).ema_indicator()
    df["ema200"] = ta.trend.EMAIndicator(df["c"], 200).ema_indicator()
    df["rsi"] = ta.momentum.RSIIndicator(df["c"], 14).rsi()
    df["atr"] = ta.volatility.AverageTrueRange(df["h"], df["l"], df["c"], 14).average_true_range()
    macd = ta.trend.MACD(df["c"])
    df["macd_hist"] = macd.macd_diff()

    last = df.iloc[-1]
    score = 0

    score += 1 if last["ema50"] > last["ema200"] else -1
    score += 1 if last["macd_hist"] > 0 else -1
    if 40 < last["rsi"] < 65:
        score += 1
    elif 35 < last["rsi"] < 60:
        score -= 1

    if score >= 2:
        side = "LONG"
    elif score <= -2:
        side = "SHORT"
    else:
        return None

    return {
        "symbol": symbol,
        "side": side,
        "score": score,
        "price": last["c"],
        "atr": last["atr"]
    }

# ===== MAIN =====
signals = []

for symbol in SYMBOLS:
    for tf in TIMEFRAMES:
        r = analyze(symbol, tf)
        if r:
            signals.append(r)

if not signals:
    send("📭 No strong futures signal")
    exit()

best = max(signals, key=lambda x: abs(x["score"]))
symbol = best["symbol"]
side = best["side"]
price = best["price"]
atr = best["atr"]

# Check existing position
if has_open_position(symbol):
    send(f"⛔ Position already open on {symbol}")
    exit()

# Set leverage
market = exchange.market(symbol)
exchange.set_leverage(LEVERAGE, market["id"])

# Position size (contracts)
amount = (POSITION_USDT * LEVERAGE) / price

# Place order
try:
    if side == "LONG":
        exchange.create_market_buy_order(symbol, amount)
    else:
        exchange.create_market_sell_order(symbol, amount)

    sl = price - 1.5 * atr if side == "LONG" else price + 1.5 * atr
    tp = price + 3 * atr if side == "LONG" else price - 3 * atr

    msg = (
        f"🚀 Futures Trade OPENED\n"
        f"Time: {datetime.utcnow()}\n\n"
        f"{'🟢' if side=='LONG' else '🔴'} {symbol}\n"
        f"Side: {side}\n"
        f"Entry: {price:.4f}\n"
        f"SL: {sl:.4f}\n"
        f"TP: {tp:.4f}\n"
        f"Size: ${POSITION_USDT}\n"
        f"Leverage: {LEVERAGE}x"
    )
    send(msg)

except Exception as e:
    send(f"❌ Order error: {e}")
