import logging

def init_logger():
    logger = logging.getLogger("crypto_bot")
    logging.basicConfig(
        filename="telegram_crypto_bot.log",
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )

    return logger

def get_logger():
    return logging.getLogger(__name__)
