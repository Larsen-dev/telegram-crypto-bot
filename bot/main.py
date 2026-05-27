import os
import yaml
import asyncio
from time import sleep
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, ContextTypes, CommandHandler, CallbackQueryHandler
from telegram.error import TimedOut

from database_controller import init_db, add_subscription, get_subscriptions
from coins_api import get_prices, get_coins, set_coins, resolve_coin_id
from logger_handler import init_logger

# Environment variables load
load_dotenv()
TELEGRAM_BOT_API_KEY = os.getenv("TELEGRAM_BOT_API_KEY")

# .yaml settings variables
with open(r"bot/settings.yaml", "r") as file:
    yaml_settings = yaml.safe_load(file)

LOGGER_SETTINGS = yaml_settings["logger_settings"]
BOT_SETTINGS = yaml_settings["bot_settings"]

LOGGER_NAME = LOGGER_SETTINGS["name"]

BOT_UPDATE_INTERVAL = BOT_SETTINGS["interval"]
BOT_DEFAULT_START_MESSAGE = BOT_SETTINGS["default_startup_message"]
BOT_MAX_MESSAGE_LENGTH = BOT_SETTINGS["max_message_length"]
BOT_MAX_RUN_TRIES = BOT_SETTINGS["max_run_tries"]

# Logging initialisation
logger = init_logger(LOGGER_NAME)

# Default start handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        text=BOT_DEFAULT_START_MESSAGE
    )

# Creates a new subsciption to some coin's cost
async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Validation
    args = context.args
    if len(args) < 3:
        await update.message.reply_text(
            "Invalid format!\nUse /subscribe <coin-name> <cost> <\"above\" | \"below\">."
        )
        return

    _coin, _price, alert_type = args[0], args[1], args[2]

    resolved_coin_id = resolve_coin_id(_coin)
    if not resolved_coin_id:
        await update.message.reply_text(
            f"Could not identify {_coin}."
        )
        return
    
    try:
        target_price = float(_price)
    except ValueError:
        await update.message.reply_text(
            f"Please, enter valid price: it should be a number!"
        )
        return
    
    if alert_type not in ["above", "below"]:
        await update.message.reply_text(
            "Please enter valid alert type: it should be \"above\" or \"below\"!"
        )
        return
    
    # Request to database
    user_id = update.effective_user.id
    add_subscription(
        user_id=user_id,
        coin=resolved_coin_id,
        target_price=target_price,
        alert_type=alert_type
    )

    await update.message.reply_text(
        "You've subscribed to coin's cost!"
    )

# Converts list of all coins into simple list of strings as they were listed
def prepare_coins_list(coins_list: [dict]):
    default = "All available coins list, page: {page}:\n"
    parts = [default + ""]

    part_index = 0
    index = 1
    for coin in coins_list:
        to_join = f"{index}. Coin name: {coin['name'].lower()}; Coin symbol: {coin['symbol'].lower()}\n"
        if len(parts[part_index]) + len(to_join) > BOT_MAX_MESSAGE_LENGTH - 1:
            # Saving one literal for page number
            parts.append(default + "")
            part_index += 1

        parts[part_index] += to_join
        index += 1

    # message_length = len(message)
    # pages = message_length // BOT_MESSAGE_LENGTH
    # leftover = pages % BOT_MESSAGE_LENGTH

    # parts = [] * pages
    # for index in range(0, pages - 1):
    #     right = index * BOT_MESSAGE_LENGTH
    #     left = message_length - pages * BOT_MESSAGE_LENGTH != leftover and (index+1) * BOT_MESSAGE_LENGTH or right + leftover
    #     part = message[right:left]

    #     parts.append(part)

    return parts

# Builds coins list page
def build_coins_list_page(parted_coins: [str], page: int):
    max_pages = len(parted_coins)

    keyboard = []
    navigation = []

    if page > 0:
        navigation.append(
            InlineKeyboardButton(
                text="Previous",
                callback_data=f"coins_{page-1}"
            )
        )
    
    if page < max_pages:
        navigation.append(
            InlineKeyboardButton(
                text="Next",
                callback_data=f"coins_{page+1}"
            )
        )
    
    if navigation:
        keyboard.append(navigation)
    
    reply_markup = InlineKeyboardMarkup(keyboard)

    return parted_coins[page].format(page=page), reply_markup

# Sends first page of coins list
async def send_coins_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text, reply_markup = build_coins_list_page(
        parted_coins=prepared_coins_list,
        page=0
    )

    await update.message.reply_text(
        text=text,
        reply_markup=reply_markup
    )

# Handles pagination of coins' list
async def handle_coins_pagination(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    page = int(query.data.split("_")[1])

    text, reply_markup = build_coins_list_page(
        parted_coins=prepared_coins_list,
        page=page
    )

    await query.edit_message_text(
        text=text,
        reply_markup=reply_markup
    )

# Checks whether someone's price have reached their target
async def check_prices_job(context: ContextTypes.DEFAULT_TYPE):
    subscriptions = get_subscriptions()
    price_map = await get_prices()

    # Checks for any equal to current price price in all subscriptions
    for subscription in subscriptions:
        coin_id = subscription["coin"]
        current_price = price_map.get(coin_id)

        if current_price is None:
            continue
        
        is_triggered = (
            (subscription["alert_type"] == "above" and current_price >= subscription["target_price"]) or
            (subscription["alert_type"] == "below" and current_price <= subscription["target_price"])
        )

        if is_triggered:
            message = (
                f"🚨 <b>Coin price alert!</b>\n 🚨"
                f"🚨 Coin {subscription['coin']} have reached or {subscription['alert_type']} target cost: {current_price}! 🚨"
            )

            try:
                await context.bot.send_message(
                    chat_id=subscription['user_id'],
                    text=message,
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.exception(
                    f"Failed to send message to {subscription['user_id']: {e}}."
                )

async def post_init(application: Application):
    global coins_list, prepared_coins_list

    init_db()

    coins_list = await get_coins()
    prepared_coins_list = prepare_coins_list(coins_list)

    await set_coins(coins_list)

async def update(context: ContextTypes.DEFAULT_TYPE):
    await check_prices_job(context)

    coins_list = await set_coins()
    prepared_coins_list = prepare_coins_list(coins_list)

# Bot's enter point
def main():
    application = Application.builder().token(TELEGRAM_BOT_API_KEY).post_init(post_init).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("subscribe", subscribe))
    application.add_handler(CommandHandler("list", send_coins_list))

    application.add_handler(CallbackQueryHandler(handle_coins_pagination, r"^coins_"))

    application.job_queue.run_repeating(update,
        interval=BOT_UPDATE_INTERVAL,
        first=5,
    )

    tries = 0
    while not application.running and tries < BOT_MAX_RUN_TRIES:
        try:
            sleep(5.0)
            application.run_polling()
        except TimedOut as e:
            tries += 1
            
            logger.exception(
                f"Failed to run application: {e}, try number: {tries}"
            )

if __name__ == "__main__":
    main()
