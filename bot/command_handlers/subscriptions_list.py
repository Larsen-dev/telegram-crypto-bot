# Global imports
import yaml
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

# Dependeices imports
from database_controller import get_subscriptions_by_user_id

# .yaml settings variables
with open(r"bot/settings.yaml", "r") as file:
    yaml_settings = yaml.safe_load(file)

BOT_SETTINGS = yaml_settings["bot_settings"]
BOT_MAX_MESSAGE_LENGTH = BOT_SETTINGS["max_message_length"]

def prepare_subscriptions_list(user_id: int):
    user_subscriptions = get_subscriptions_by_user_id(user_id)

    default = "All your subscriptions, page: {page}:\n"
    parts = [default + ""]

    part_index = 0
    index = 1
    for subscription in user_subscriptions:
        to_join = (
            f"{index}. Coin: {subscription['coin']},"
            f"target price: {subscription['target_price']},"
            f"alert type: {subscription['alert_type']},"
            f"subscription id: {subscription['id']}\n"
        )
        if len(parts[part_index]) + len(to_join) > BOT_MAX_MESSAGE_LENGTH - 1:
            # Saving one literal for page number
            parts.append(default + "")
            part_index += 1

        parts[part_index] += to_join
        index += 1

    return parts

def build_subscriptions_list_page(parted_subscriptions: [str], page: int):
    max_pages = len(parted_subscriptions)

    keyboard = []
    navigation = []

    if page > 0:
        navigation.append(
            InlineKeyboardButton(
                text="Previous",
                callback_data=f"subscription_{page-1}"
            )
        )
    
    if page < max_pages:
        navigation.append(
            InlineKeyboardButton(
                text="Next",
                callback_data=f"subscription_{page+1}"
            )
        )
    
    if navigation:
        keyboard.append(navigation)
    
    reply_markup = InlineKeyboardMarkup(keyboard)

    return parted_subscriptions[page].format(page=page), reply_markup

async def handle_subscriptions_list_pagination(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    parted_subscriptions = prepare_subscriptions_list(update.effective_user.id)
    page = min(int(query.data.split("_")[1]), len(parted_subscriptions) - 1)

    text, reply_markup = build_subscriptions_list_page(
        parted_subscriptions=parted_subscriptions,
        page=page
    )

    await query.edit_message_text(
        text=text,
        reply_markup=reply_markup
    )

async def send_subscriptions_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    parted_subscriptions = prepare_subscriptions_list(update.effective_user.id)

    text, reply_markup = build_subscriptions_list_page(
        parted_subscriptions=parted_subscriptions,
        page=0
    )

    await update.message.reply_text(
        text=text,
        reply_markup=reply_markup
    )