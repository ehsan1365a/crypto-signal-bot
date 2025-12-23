import ccxt
import os
import requests

# ================== TELEGRAM ==================
TELEGRAM_TOKEN = os.getenv("telegram_token")
CHAT_ID = os.getenv("chat_id")

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": msg}
    requests.post(url, data=data)

# ================== COINEX ==================
exchange = ccxt.coinex({
    "apiKey": os.getenv("COINEX_API_KEY"),
    "secret": os.getenv("COINEX_API_SECRET"),
    "enableRateLimit": True,
    "options": {
        "defaultType": "swap",
        "createMarketBuyOrderRequiresPrice": False
    }
})

# ✅ سمبل صحیح فیوچرز
symbol = "BTC/USDT:USDT"

trade_cost = 8  # USDT واقعی (ایمن با 25 دلار)

send_telegram("🚀 Futures Bot Started")

try:
    ticker = exchange.fetch_ticker(symbol)
    price = ticker["last"]

    amount = trade_cost / price

    order = exchange.create_market_buy_order(
        symbol=symbol,
        amount=amount
    )

    send_telegram(
        f"✅ Order Opened\n\n"
        f"Symbol: BTC Futures\n"
        f"Side: LONG\n"
        f"Entry: {price}\n"
        f"Size: {trade_cost} USDT\n"
        f"Leverage: Manual (3x)"
    )

except Exception as e:
    send_telegram(f"❌ Order error: {str(e)}")

send_telegram("⏹ Bot Finished")
