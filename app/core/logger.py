import logging
import os

# Create logs directory if it doesn't exist
LOGS_DIR = os.path.join(os.path.dirname(__file__), "../../logs")
os.makedirs(LOGS_DIR, exist_ok=True)

# Configure logging
LOG_FILE_PATH = os.path.join(LOGS_DIR, "app.log")

# LOG_LEVEL is read straight from the environment (not ConfigProvider) so
# logging works before, and while, the configuration is loaded.
DEFAULT_LOG_LEVEL = "INFO"
_requested_level = (os.getenv("LOG_LEVEL") or DEFAULT_LOG_LEVEL).strip().upper()
LOG_LEVEL = _requested_level if _requested_level in logging.getLevelNamesMapping() else DEFAULT_LOG_LEVEL

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE_PATH),  # Log to file
        logging.StreamHandler()  # Log to console
    ]
)

# Create a logger instance
logger = logging.getLogger(__name__)

if LOG_LEVEL != _requested_level:
    logger.warning("Unknown LOG_LEVEL %r, using %s", _requested_level, DEFAULT_LOG_LEVEL)

if __name__ == "__main__":
    # Test logs
    logger.debug("This is a DEBUG message.")
    logger.info("This is an INFO message.")
    logger.warning("This is a WARNING message.")
    logger.error("This is an ERROR message.")
    logger.critical("This is a CRITICAL message.")
