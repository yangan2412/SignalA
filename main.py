#!/usr/bin/env python3
"""
SignalA - Telegram Trading Signal Bot
Phân tích lịch sử giao dịch BingX và gửi tín hiệu Long/Short
"""

import asyncio
import logging
from config import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/bot.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

async def main():
    """Main entry point"""
    try:
        # Validate settings
        settings.validate()
        logger.info("Settings validated successfully")

        # TODO: Initialize components
        logger.info("Starting SignalA Trading Bot...")
        logger.info(f"Monitoring pairs: {', '.join(settings.TRADING_PAIRS)}")
        logger.info(f"Timeframe: {settings.DEFAULT_TIMEFRAME}")

        # Keep the bot running
        while True:
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    asyncio.run(main())
