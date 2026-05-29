# Global imports
import yaml
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

# .yaml settings variables
with open(r"bot/settings.yaml", "r") as file:
    yaml_settings = yaml.safe_load(file)

BOT_SETTINGS = yaml_settings["bot_settings"]
BOT_MAX_MESSAGE_LENGTH = BOT_SETTINGS["max_message_length"]

# Converts list of all coins into simple list of strings as they were listed
def prepare_coins_list(coins_list: [dict]) -> [str]:
    default = "All available coins list, page: {page}:\n"

    global prepared_coins_list
    prepared_coins_list = [default + ""]

    part_index = 0
    index = 1
    for coin in coins_list:
        to_join = f"{index}. Coin name: {coin['name'].lower()}; Coin symbol: {coin['symbol'].lower()}\n"
        if len(prepared_coins_list[part_index]) + len(to_join) > BOT_MAX_MESSAGE_LENGTH - 1:
            # Saving one literal for page number
            prepared_coins_list.append(default + "")
            part_index += 1

        prepared_coins_list[part_index] += to_join
        index += 1

    return prepared_coins_list

# Builds coins list page
def build_coins_list_page(parted_coins: [str], page: int) -> (str, InlineKeyboardButton):
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
async def handle_coins_list_pagination(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    page = min(int(query.data.split("_")[1]), len(prepared_coins_list) - 1)

    text, reply_markup = build_coins_list_page(
        parted_coins=prepared_coins_list,
        page=page
    )

    await query.edit_message_text(
        text=text,
        reply_markup=reply_markup
    )