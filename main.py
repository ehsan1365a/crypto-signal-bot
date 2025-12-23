import ccxt
import os
import time
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

symbol = "BTC/USDT"
leverage = 3
trade_cost = 8  # USDT واقعی

# ================== START ==================
send_telegram("🚀 Futures Bot Started")

try:
    exchange.set_leverage(leverage, symbol)
    ticker = exchange.fetch_ticker(symbol)
    price = ticker["last"]

    amount = trade_cost / price  # مقدار قرارداد

    order = exchange.create_market_buy_order(
        symbol=symbol,
        amount=amount
    )

    send_telegram(
        f"✅ Order Opened\n\n"
        f"Symbol: {symbol}\n"
        f"Side: LONG\n"
        f"Price: {price}\n"
        f"Size: {trade_cost} USDT\n"
        f"Leverage: {leverage}x"
    )

except Exception as e:
    send_telegram(f"❌ Order error: {str(e)}")

send_telegram("⏹ Bot Finished")
