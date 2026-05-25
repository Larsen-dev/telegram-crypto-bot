import httpx

from logger_handler import get_logger

COIN_API_URL = "https://api.coinpaprika.com/v1"

logger = get_logger()

def resolve_coin_id(user_input: str):
    formatted = user_input.strip().lower()

    if formatted in SYMBOL_TO_ID.values():
        return formatted
    
    if formatted in SYMBOL_TO_ID:
        return SYMBOL_TO_ID[formatted]
    
    if formatted in NAME_TO_ID:
        return NAME_TO_ID[formatted]
    
    return None

async def get_coins():
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{COIN_API_URL}/coins",
                timeout=10
            )
            if response.status_code != 200:
                logger.exception(
                    f"CoinPaprika API request failed, staus code: {response.status_code}"
                )
            
            coins_list = response.json()
        except Exception as e:
            logger.exception(
                f"CoinPaprika API request failed: {e}"
            )
    
    return coins_list

async def set_coins():
    global SYMBOL_TO_ID, NAME_TO_ID
    coins_list = get_coins()

    for coin in coins_list:
        coin_id = coin["id"]
        symbol = coin["symbol"].lower()
        name = coin["name"].lower()

        if coin.get("is_active", True):
            if symbol not in SYMBOL_TO_ID:
                SYMBOL_TO_ID[symbol] = coin_id

            if name not in NAME_TO_ID:
                NAME_TO_ID[name] = coin_id

async def get_prices(subscriptions: dict):
    coins = ",".join(list(set(subscription["coin"] for subscription in subscriptions)))

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{COIN_API_URL}/tickers",
                timeout=10
            )
            if response.status_code != 200:
                return
            
            ticker_list = response.json()
        except Exception as e:
            logger.exception(
                f"CoinPaprika API request failed: {e}"
            )
    
    price_map = {}
    for ticker in ticker_list:
        coin_id = ticker.get("id")
        price = ticker.get("quotes", {}).get("USD", {}).get("price")
        price_map[coin_id] = price
    
    return price_map
