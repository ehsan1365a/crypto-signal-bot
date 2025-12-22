import ccxt
import os
import requests
import pandas as pd
from datetime import datetime

# =======================
# CONFIG
# =======================
SYMBOLS = ["SOL/USDT", "ADA/USDT", "XRP/USDT", "DOGE/USDT", "BNB/USDT"]
TIMEFRAME = "15m"
LEVERAGE = 3
POSITION_USDT = 18

ATR_PERIOD = 14
ATR_SL = 1.5
ATR_TP = 3.0

# =======================
# TELEGRAM
# =======================
TG_TOKEN = os.getenv("telegram_token")
CHAT_ID = os.getenv("chat_id")

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

# =======================
# EXCHANGE
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

exchange.load_markets()

# =======================
# INDICATORS
# =======================
def get_atr(df, period=14):
    tr = pd.concat([
        df["high"] - df["low"],
        abs(df["high"] - df["close"].shift()),
        abs(df["low"] - df["close"].shift())
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def signal_strength(df, atr):
    return abs(df["close"].iloc[-1] - df["close"].iloc[-2]) / atr if atr else 0

# =======================
# MAIN
# =======================
def run_bot():
    candidates = []

    for symbol in SYMBOLS:
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, TIMEFRAME, limit=100)
            df = pd.DataFrame(ohlcv, columns=["t","open","high","low","close","vol"])
            price = df["close"].iloc[-1]
            atr = get_atr(df).iloc[-1]

            side = "LONG" if df["close"].iloc[-1] > df["close"].iloc[-2] else "SHORT"
            strength = signal_strength(df, atr)

            raw_amount = (POSITION_USDT * LEVERAGE) / price
            min_amount = exchange.market(symbol)["limits"]["amount"]["min"]

            if raw_amount < min_amount:
                send_telegram(f"⚠️ {symbol} skipped (amount too small)")
                continue

            amount = round(raw_amount, 3)

            candidates.append({
                "symbol": symbol,
                "side": side,
                "price": price,
                "atr": atr,
                "strength": strength,
                "amount": amount
            })

        except Exception as e:
            send_telegram(f"❌ {symbol} fetch error: {e}")

    if not candidates:
        send_telegram("❌ No valid trades (capital too low)")
        return

    trade = max(candidates, key=lambda x: x["strength"])

    sl = trade["price"] - ATR_SL * trade["atr"] if trade["side"] == "LONG" else trade["price"] + ATR_SL * trade["atr"]
    tp = trade["price"] + ATR_TP * trade["atr"] if trade["side"] == "LONG" else trade["price"] - ATR_TP * trade["atr"]

    try:
        if trade["side"] == "LONG":
            exchange.create_market_buy_order(trade["symbol"], trade["amount"])
        else:
            exchange.create_market_sell_order(trade["symbol"], trade["amount"])

        send_telegram(
f"""📡 Futures Trade Bot
Time: {datetime.utcnow()}

{'🟢' if trade['side']=='LONG' else '🔴'} {trade['symbol']}
Side: {trade['side']}
Entry: {trade['price']:.4f}
SL: {sl:.4f}
TP: {tp:.4f}
Size: ${POSITION_USDT}
Leverage: {LEVERAGE}x"""
        )

    except Exception as e:
        send_telegram(f"❌ Order error: {e}")

# =======================
run_bot()
