import ccxt, os, requests, time

# ===== TELEGRAM =====
TOKEN = os.getenv("telegram_token")
CHAT_ID = os.getenv("chat_id")

def send(msg):
    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        data={"chat_id": CHAT_ID, "text": msg}
    )

# ===== COINEX =====
exchange = ccxt.coinex({
    "apiKey": os.getenv("COINEX_API_KEY"),
    "secret": os.getenv("COINEX_API_SECRET"),
    "enableRateLimit": True,
    "options": {
        "defaultType": "swap",
        "createMarketBuyOrderRequiresPrice": False
    }
})

SYMBOLS = [
    "ADA/USDT:USDT",
    "XRP/USDT:USDT",
    "DOGE/USDT:USDT"
]

USDT_PER_TRADE = 8
TP_PERCENT = 0.8
SL_PERCENT = 0.5

send("🚀 Auto Futures Bot Started")

def atr(ohlcv, period=14):
    trs = []
    for i in range(1, len(ohlcv)):
        high = ohlcv[i][2]
        low = ohlcv[i][3]
        prev_close = ohlcv[i-1][4]
        tr = max(high-low, abs(high-prev_close), abs(low-prev_close))
        trs.append(tr)
    return sum(trs[-period:]) / period

try:
    markets = exchange.load_markets()
    best = None

    for symbol in SYMBOLS:
        ohlcv = exchange.fetch_ohlcv(symbol, "15m", limit=20)
        last = ohlcv[-1]

        body = abs(last[4] - last[1])
        a = atr(ohlcv)

        if a == 0:
            continue

        strength = body / a
        side = "buy" if last[4] > last[1] else "sell"

        if not best or strength > best["strength"]:
            best = {
                "symbol": symbol,
                "side": side,
                "strength": strength,
                "price": last[4]
            }

    if not best:
        send("❌ No valid signal found")
    else:
        symbol = best["symbol"]
        side = best["side"]
        price = best["price"]

        market = markets[symbol]
        min_amount = market["limits"]["amount"]["min"]

        amount = USDT_PER_TRADE / price
        if amount < min_amount:
            amount = min_amount

        amount = float(exchange.amount_to_precision(symbol, amount))

        exchange.create_market_order(symbol, side, amount)

        if side == "buy":
            tp = price * (1 + TP_PERCENT/100)
            sl = price * (1 - SL_PERCENT/100)
            close_side = "sell"
            side_txt = "LONG"
        else:
            tp = price * (1 - TP_PERCENT/100)
            sl = price * (1 + SL_PERCENT/100)
            close_side = "buy"
            side_txt = "SHORT"

        time.sleep(2)

        exchange.create_order(
            symbol, "limit", close_side, amount,
            exchange.price_to_precision(symbol, tp),
            {"reduce_only": True}
        )

        exchange.create_order(
            symbol, "stop_market", close_side, amount,
            params={
                "stopPrice": exchange.price_to_precision(symbol, sl),
                "reduce_only": True
            }
        )

        send(
            f"✅ BEST SIGNAL TRADED\n\n"
            f"Symbol: {symbol}\n"
            f"Side: {side_txt}\n"
            f"Entry: {price:.4f}\n"
            f"Amount: {amount}\n"
            f"TP: {tp:.4f}\n"
            f"SL: {sl:.4f}"
        )

except Exception as e:
    send(f"❌ Bot Error: {str(e)}")

send("⏹ Bot Finished")
