import logging

# Gets logger by passed name
def init_logger(logger_name: str):
    logger = logging.getLogger(logger_name)
    logging.basicConfig(
        filename=f"{logger_name}.log",
        filemode="w",
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )

    return logger

# Returnes logger
def get_logger(logger_name: str):
    return logging.getLogger(logger_name)
