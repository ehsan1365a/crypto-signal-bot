import ccxt
import os
import requests

# ========= TELEGRAM =========
TOKEN = os.getenv("telegram_token")
CHAT_ID = os.getenv("chat_id")

def send(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

# ========= COINEX =========
exchange = ccxt.coinex({
    "apiKey": os.getenv("COINEX_API_KEY"),
    "secret": os.getenv("COINEX_API_SECRET"),
    "enableRateLimit": True,
    "options": {
        "defaultType": "swap",
        "createMarketBuyOrderRequiresPrice": False
    }
})

SYMBOL = "ADA/USDT:USDT"
TRADE_USDT = 8  # امن

send("🚀 Futures Bot Started")

try:
    markets = exchange.load_markets()
    market = markets[SYMBOL]

    price = exchange.fetch_ticker(SYMBOL)["last"]

    min_amount = market["limits"]["amount"]["min"]

    amount = TRADE_USDT / price

    # ✅ اصلاح اتومات حداقل حجم
    if amount < min_amount:
        amount = min_amount

    amount = float(exchange.amount_to_precision(SYMBOL, amount))

    order = exchange.create_market_buy_order(
        symbol=SYMBOL,
        amount=amount
    )

    send(
        f"✅ Order Opened\n\n"
        f"Symbol: ADA Futures\n"
        f"Entry: {price}\n"
        f"Amount: {amount}\n"
        f"Margin: {TRADE_USDT} USDT\n"
        f"MinAmount: {min_amount}"
    )

except Exception as e:
    send(f"❌ Order error: {str(e)}")

send("⏹ Bot Finished")
