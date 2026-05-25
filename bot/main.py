import os
import yaml
import asyncio
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, ContextTypes, CommandHandler

from database_controller import init_db, add_subscription, get_subscriptions
from coins_api import get_prices, get_coins, set_coins, resolve_coin_id
from logger_handler import init_logger

# Environment variables load
load_dotenv()
TELEGRAM_BOT_API_KEY = os.getenv("TELEGRAM_BOT_API_KEY")

# Logging initialisation
logger = init_logger()

# Default start handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Crypto bot is active!\nUse /subscribe <coin-name> <cost> <\"above\" | \"below\">."
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

async def send_coins_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    coins_list = await get_coins()
    message = "All available coins list:\n"

    index = 1
    for coin in coins_list:
        message.join(f"{index}. Coin name: {coin['name'].lower()}; Coin symbol: {coin['symbol'].lower()}\n")
        index += 1
    
    await update.message.reply_text(
        text=message,
        parse_mode="HTML"
    )

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

# Bot's enter point
def main():
    init_db()
    asyncio.get_event_loop().run_until_complete(set_coins())

    application = Application.builder().token(TELEGRAM_BOT_API_KEY).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("subscribe", subscribe))

    job_queue = application.job_queue
    job_queue.run_repeating(check_prices_job, interval=300, first=5)

    application.run_polling()

if __name__ == "__main__":
    main()
