import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Settings:
    # BingX API
    BINGX_API_KEY = os.getenv("BINGX_API_KEY", "")
    BINGX_SECRET_KEY = os.getenv("BINGX_SECRET_KEY", "")
    BINGX_BASE_URL = os.getenv("BINGX_BASE_URL", "https://open-api.bingx.com")

    # Telegram Bot
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

    # Trading Configuration
    TRADING_PAIRS = os.getenv("TRADING_PAIRS", "BTC-USDT").split(",")
    DEFAULT_TIMEFRAME = os.getenv("DEFAULT_TIMEFRAME", "1h")
    SIGNAL_CONFIDENCE_THRESHOLD = float(os.getenv("SIGNAL_CONFIDENCE_THRESHOLD", "0.7"))

    # Symbol Selection
    SYMBOL_MODE = os.getenv("SYMBOL_MODE", "whitelist")  # 'whitelist' or 'volatility'
    VOLATILITY_TOP_N = int(os.getenv("VOLATILITY_TOP_N", "20"))
    VOLATILITY_MIN_VOLUME = float(os.getenv("VOLATILITY_MIN_VOLUME", "1000000"))

    # Martingale Configuration
    ENABLE_MARTINGALE = os.getenv("ENABLE_MARTINGALE", "true").lower() == "true"
    MARTINGALE_MAX_STEPS = int(os.getenv("MARTINGALE_MAX_STEPS", "5"))
    MARTINGALE_TRIGGER_PCT = float(os.getenv("MARTINGALE_TRIGGER_PCT", "15.0"))

    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///signala.db")

    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    @classmethod
    def validate(cls):
        """Validate required settings"""
        required = [
            ("BINGX_API_KEY", cls.BINGX_API_KEY),
            ("BINGX_SECRET_KEY", cls.BINGX_SECRET_KEY),
            ("TELEGRAM_BOT_TOKEN", cls.TELEGRAM_BOT_TOKEN),
            ("TELEGRAM_CHAT_ID", cls.TELEGRAM_CHAT_ID),
        ]

        missing = [name for name, value in required if not value]
        if missing:
            raise ValueError(f"Missing required settings: {', '.join(missing)}")

        return True

settings = Settings()
