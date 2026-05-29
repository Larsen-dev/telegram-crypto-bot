import asyncio
import os

from telegram import Bot

TOKEN = os.getenv("TELEGRAM_BOT_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

async def main():
    bot = Bot(TOKEN)

    await bot.set_webhook(WEBHOOK_URL)

    print("Webhook installed!")

asyncio.run(main())
