import ccxt, os, requests

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

send("🚀 Auto Futures Bot Started")

def atr(ohlcv, period=14):
    trs = []
    for i in range(1, len(ohlcv)):
        h, l = ohlcv[i][2], ohlcv[i][3]
        pc = ohlcv[i-1][4]
        trs.append(max(h-l, abs(h-pc), abs(l-pc)))
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
        send("❌ No strong signal found")
    else:
        symbol = best["symbol"]
        side = best["side"]
        price = best["price"]

        min_amount = markets[symbol]["limits"]["amount"]["min"]
        amount = USDT_PER_TRADE / price
        if amount < min_amount:
            amount = min_amount

        amount = float(exchange.amount_to_precision(symbol, amount))

        exchange.create_market_order(symbol, side, amount)

        send(
            f"✅ BEST SIGNAL EXECUTED\n\n"
            f"Symbol: {symbol}\n"
            f"Side: {'LONG' if side=='buy' else 'SHORT'}\n"
            f"Entry: {price:.4f}\n"
            f"Amount: {amount}"
        )

except Exception as e:
    send(f"❌ Bot Error: {str(e)}")

send("⏹ Bot Finished")
