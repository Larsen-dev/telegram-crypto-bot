import yaml
import httpx

from logger_handler import get_logger

# Default variables
COIN_API_URL = "https://api.coinpaprika.com/v1"
SYMBOL_TO_ID, NAME_TO_ID = {}, {}

# Settings
with open(r"bot/settings.yaml", "r") as file:
    LOGGER_SETTINGS = yaml.safe_load(file)["logger_settings"]

LOGGER_NAME = LOGGER_SETTINGS["name"]

# Logger initialisation
logger = get_logger(LOGGER_NAME)

# Resolves whether passed input is a valid coin and returnes its id
def resolve_coin_id(user_input: str):
    formatted = user_input.strip().lower()

    if formatted in SYMBOL_TO_ID.values():
        return formatted
    
    if formatted in SYMBOL_TO_ID:
        return SYMBOL_TO_ID[formatted]
    
    if formatted in NAME_TO_ID:
        return NAME_TO_ID[formatted]
    
    return None

# Gets list of all coins
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

# Sets default global variables as SYMBOL_TO_ID and NAME_TO_ID needed for resolving
async def set_coins(coins_list: dict):
    for coin in coins_list:
        coin_id = coin["id"]
        symbol = coin["symbol"].lower()
        name = coin["name"].lower()

        if coin.get("is_active", True):
            if symbol not in SYMBOL_TO_ID:
                SYMBOL_TO_ID[symbol] = coin_id

            if name not in NAME_TO_ID:
                NAME_TO_ID[name] = coin_id

# Gets prices of all available coins
async def get_prices():
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
