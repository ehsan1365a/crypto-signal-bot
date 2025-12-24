import ccxt
import os
import pandas as pd
import numpy as np

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

RISK_USDT = 8
LEVERAGE = 3
ATR_SL = 1.2
ATR_TP = 2.0

# =======================
# Indicators
# =======================
def atr(df, period=14):
    tr = np.maximum(
        df["high"] - df["low"],
        np.maximum(
            abs(df["high"] - df["close"].shift()),
            abs(df["low"] - df["close"].shift())
        )
    )
    return tr.rolling(period).mean()

def get_signal(symbol, tf):
    ohlcv = exchange.fetch_ohlcv(symbol, tf, limit=100)
    df = pd.DataFrame(ohlcv, columns=["ts","open","high","low","close","vol"])

    df["ema20"] = df["close"].ewm(span=20).mean()
    df["ema50"] = df["close"].ewm(span=50).mean()
    df["atr"] = atr(df)

    last = df.iloc[-1]

    if last["ema20"] > last["ema50"]:
        return "LONG", float(last["atr"])
    elif last["ema20"] < last["ema50"]:
        return "SHORT", float(last["atr"])

    return None, None

# =======================
# Find Best Signal
# =======================
def find_best_signal():
    best = None

    for symbol in SYMBOLS:
        sides = []
        atrs = []

        for tf in TIMEFRAMES:
            side, atr_val = get_signal(symbol, tf)
            if side:
                sides.append(side)
                atrs.append(atr_val)

        if len(sides) == len(TIMEFRAMES) and sides.count(sides[0]) == len(sides):
            avg_atr = float(np.mean(atrs))

            if best is None or avg_atr > best["atr"]:
                best = {
                    "symbol": symbol,
                    "side": sides[0],
                    "atr": avg_atr
                }

    return best

# =======================
# Execute Trade + SL/TP
# =======================
def execute_trade(signal):
    symbol = signal["symbol"]
    side = signal["side"]
    atr_val = signal["atr"]

    exchange.set_leverage(LEVERAGE, symbol)
    price = exchange.fetch_ticker(symbol)["last"]

    amount = round((RISK_USDT * LEVERAGE) / price, 4)
    if amount <= 0:
        raise Exception("Amount too small")

    if side == "LONG":
        exchange.create_market_buy_order(symbol, amount)

        sl = price - ATR_SL * atr_val
        tp = price + ATR_TP * atr_val

        exchange.create_order(
            symbol, "market", "sell", amount, None,
            {
                "stop": "loss",
                "stop_price": round(sl, 4),
                "reduce_only": True
            }
        )

        exchange.create_order(
            symbol, "market", "sell", amount, None,
            {
                "stop": "entry",
                "stop_price": round(tp, 4),
                "reduce_only": True
            }
        )

    else:
        exchange.create_market_sell_order(symbol, amount)

        sl = price + ATR_SL * atr_val
        tp = price - ATR_TP * atr_val

        exchange.create_order(
            symbol, "market", "buy", amount, None,
            {
                "stop": "loss",
                "stop_price": round(sl, 4),
                "reduce_only": True
            }
        )

        exchange.create_order(
            symbol, "market", "buy", amount, None,
            {
                "stop": "entry",
                "stop_price": round(tp, 4),
                "reduce_only": True
            }
        )

    send_telegram(
        f"✅ TRADE OPENED + SL/TP SET\n\n"
        f"Symbol: {symbol}\n"
        f"Side: {side}\n"
        f"Entry: {round(price,4)}\n"
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
    if signal:
        execute_trade(signal)
    else:
        send_telegram("❌ No strong signal found")
except Exception as e:
    send_telegram(f"❌ Bot Error: {str(e)}")

send_telegram("⏹ Bot Finished")
