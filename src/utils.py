# src/utils.py
import logging
import os
import sys
import io

LOG_FILE = os.path.join("logs", "trading_bot.log")

def setup_logging():
    """Configures the application logger."""
    # Use a fixed name so all modules share the same logger instance
    logger = logging.getLogger("trading_bot")
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        log_dir = os.path.dirname(LOG_FILE)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)

        # File Handler
        file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
        file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(logging.INFO)
        logger.addHandler(file_handler)

        # Console Handler
        try:
            if hasattr(sys.stdout, "buffer"):
                console_stream = io.TextIOWrapper(
                    sys.stdout.buffer,
                    encoding="utf-8",
                    errors="replace",
                    line_buffering=True,
                )
            else:
                console_stream = sys.stdout
        except Exception:
            console_stream = sys.stdout

        console_handler = logging.StreamHandler(console_stream)
        console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(console_formatter)
        console_handler.setLevel(logging.INFO)
        logger.addHandler(console_handler)

    return logger

logger = setup_logging()
