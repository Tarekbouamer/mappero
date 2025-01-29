__version__ = "0.1.0"

from mappero.utils.logger import setup_logger

try:
    from loguru import logger

    setup_logger(app_name="mappero")

except ImportError:
    import logging

    logger = logging.getLogger(__name__)
    logger.warning("Could not import loguru")
