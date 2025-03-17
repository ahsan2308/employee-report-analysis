import logging
import os

# Create logs directory if it doesn't exist
LOGS_DIR = os.path.join(os.path.dirname(__file__), "../../logs")
os.makedirs(LOGS_DIR, exist_ok=True)

# Configure logging
LOG_FILE_PATH = os.path.join(LOGS_DIR, "app.log")

logging.basicConfig(
    level=logging.DEBUG,  # Set to logging.INFO in production
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE_PATH),  # Log to file
        logging.StreamHandler()  # Log to console
    ]
)

# Create a logger instance
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    # Test logs
    logger.debug("This is a DEBUG message.")
    logger.info("This is an INFO message.")
    logger.warning("This is a WARNING message.")
    logger.error("This is an ERROR message.")
    logger.critical("This is a CRITICAL message.")
