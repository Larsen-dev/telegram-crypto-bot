# Library dependecies
import os
import yaml
import asyncio
from time import sleep
from dotenv import load_dotenv
from telegram import Update, BotCommand, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, ContextTypes, CommandHandler, CallbackQueryHandler
from telegram.error import TimedOut

# API dependecies
from database_controller import init_db, add_subscription, get_subscriptions, get_subscriptions_by_user_id, set_inactive
from coins_api import get_prices, get_coins, set_coins, resolve_coin_id
from logger_handler import init_logger
from command_handlers.coins_list import prepare_coins_list, send_coins_list, handle_coins_list_pagination
from command_handlers.subscriptions_list import prepare_subscriptions_list, send_subscriptions_list, handle_subscriptions_list_pagination

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
MAX_SUBSCRIPTIONS_PER_USER = BOT_SETTINGS["max_subscriptions_per_user"]
COST_DIFFERENCE_PERCENT = BOT_SETTINGS["cost_difference_percent"]

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

async def unsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Validation
    args = context.args
    if len(args) < 1:
        await update.message.reply_text(
            "Invalid format!\nUse /unsubscribe <subscription_id>."
        )
        return

    _subscription_id = args[0]

    try:
        subscription_id = int(_subscription_id)
    except ValueError:
        await update.message.reply_text(
            f"Please, enter valid subscription id: it should be a number!"
        )
        return
    
    set_inactive(
        subscription_id=subscription_id
    )

    await update.message.reply_text(
        "You've unsubscribed from coin's cost!"
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

        difference = subscription["target_price"] / 100 * COST_DIFFERENCE_PERCENT
        target_price = subscription["target_price"]

        is_triggered = (
            (
                subscription["alert_type"] == "above"
                and current_price >= target_price + difference
            )
            or
            (
                subscription["alert_type"] == "below"
                and current_price <= target_price - difference
            )
        )

        if is_triggered:
            message = (
                f"🚨 <b>Coin price alert!</b> 🚨\n"
                f"🚨 Coin {subscription['coin']} have reached or {subscription['alert_type']} target cost: {current_price} USD! 🚨"
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
    global logger

    init_db()

    await application.bot.set_my_commands([
        BotCommand("start", "Starts the bot"),
        BotCommand("subscribe", "Subscribe to coin alerts"),
        BotCommand("unsubscribe", "Unsubscribe to coin alerts"),
        BotCommand("coins_list", "Show available coins"),
        BotCommand("subscriptions_list", "Show current active subscriptions"),
    ])

    # Logging initialisation
    logger = init_logger(LOGGER_NAME)

    coins_list = await get_coins()
    prepared_coins_list = prepare_coins_list(coins_list)

    await set_coins(coins_list)

async def update(context: ContextTypes.DEFAULT_TYPE):
    await check_prices_job(context)

    coins_list = await get_coins()
    prepared_coins_list = prepare_coins_list(coins_list)

    await set_coins(coins_list)

# Bot's enter point
def main():
    application = Application.builder().token(TELEGRAM_BOT_API_KEY).post_init(post_init).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("subscribe", subscribe))
    application.add_handler(CommandHandler("unsubscribe", unsubscribe))
    application.add_handler(CommandHandler("coins_list", send_coins_list))
    application.add_handler(CommandHandler("subscriptions_list", send_subscriptions_list))

    application.add_handler(CallbackQueryHandler(handle_coins_list_pagination, r"^coins_"))
    application.add_handler(CallbackQueryHandler(handle_subscriptions_list_pagination, r"^subscription_"))

    application.job_queue.run_repeating(
        callback=update,
        interval=BOT_UPDATE_INTERVAL,
        first=5,
    )

    try:
        application.run_polling(
            drop_pending_updates=True,
            allowed_updates=Update.ALL_TYPES,
        )
    except KeyboardInterrupt:
        logger.info("Bot stopped.")

if __name__ == "__main__":
    main()
