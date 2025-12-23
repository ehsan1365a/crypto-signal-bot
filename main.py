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

# ✅ ارز مناسب سرمایه کم
SYMBOL = "ADA/USDT:USDT"

TRADE_USDT = 8  # امن با 25 دلار

send("🚀 Futures Bot Started")

try:
    price = exchange.fetch_ticker(SYMBOL)["last"]

    # محاسبه مقدار + گرد کردن امن
    amount = round(TRADE_USDT / price, 2)

    order = exchange.create_market_buy_order(
        symbol=SYMBOL,
        amount=amount
    )

    send(
        f"✅ Order Opened\n\n"
        f"Symbol: ADA Futures\n"
        f"Side: LONG\n"
        f"Entry: {price}\n"
        f"Amount: {amount}\n"
        f"Margin: {TRADE_USDT} USDT"
    )

except Exception as e:
    send(f"❌ Order error: {str(e)}")

send("⏹ Bot Finished")
