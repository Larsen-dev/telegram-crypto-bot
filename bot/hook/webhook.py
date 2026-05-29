import os
import asyncio

from flask import Flask, request

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
)

from main import (
    start,
    subscribe,
    unsubscribe,
    send_coins_list,
    send_subscriptions_list,
    handle_coins_list_pagination,
    handle_subscriptions_list_pagination,
    post_init,
)

TOKEN = os.getenv("TELEGRAM_BOT_API_KEY")

app = Flask(__name__)

telegram_app = (
    Application.builder()
    .token(TOKEN)
    .post_init(post_init)
    .build()
)

telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("subscribe", subscribe))
telegram_app.add_handler(CommandHandler("unsubscribe", unsubscribe))
telegram_app.add_handler(CommandHandler("coins_list", send_coins_list))
telegram_app.add_handler(CommandHandler("subscriptions_list", send_subscriptions_list))

telegram_app.add_handler(
    CallbackQueryHandler(
        handle_coins_list_pagination,
        pattern=r"^coins_"
    )
)

telegram_app.add_handler(
    CallbackQueryHandler(
        handle_subscriptions_list_pagination,
        pattern=r"^subscription_"
    )
)

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

loop.run_until_complete(telegram_app.initialize())
loop.run_until_complete(telegram_app.start())

@app.post("/")
def webhook():
    update = Update.de_json(
        request.get_json(force=True),
        telegram_app.bot
    )

    loop.run_until_complete(
        telegram_app.process_update(update)
    )

    return "ok"
