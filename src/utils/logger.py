from loguru import logger
import sys

def setup_logger(log_level: str = "INFO"):
    """Configure logger for Cypher"""
    logger.remove()
    logger.add(
        sys.stdout,
        colorize=True,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
        level=log_level
    )
    logger.add(
        "data/logs/cypher_{time}.log",
        rotation="1 day",
        retention="7 days",
        level=log_level
    )
    return logger
