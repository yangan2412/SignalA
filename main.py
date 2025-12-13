#!/usr/bin/env python3
"""
SignalA - Telegram Trading Signal Bot
Phân tích lịch sử giao dịch BingX và gửi tín hiệu Long/Short
"""

import asyncio
import logging
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta

from config import settings
from src.api.bingx_client import BingXClient
from src.analysis.trade_analyzer import TradeAnalyzer
from src.strategies.learned_strategy import LearnedStrategy
from src.bot.telegram_bot import TradingSignalBot
from src.bot.signal_manager import SignalManager

# Configure logging
Path('logs').mkdir(exist_ok=True)
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/bot.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class SignalABot:
    """Main bot orchestrator"""

    def __init__(self):
        self.bingx_client = None
        self.telegram_bot = None
        self.strategy = None
        self.signal_manager = SignalManager(cooldown_minutes=30)
        self.is_running = False

    async def initialize(self):
        """Initialize all components"""
        logger.info("Initializing SignalA Bot...")

        # Validate settings
        settings.validate()

        # Initialize BingX client
        self.bingx_client = BingXClient(
            api_key=settings.BINGX_API_KEY,
            secret_key=settings.BINGX_SECRET_KEY,
            base_url=settings.BINGX_BASE_URL
        )

        # Test connection
        if not self.bingx_client.test_connection():
            raise Exception("Failed to connect to BingX API")

        # Initialize Telegram bot
        self.telegram_bot = TradingSignalBot(
            bot_token=settings.TELEGRAM_BOT_TOKEN,
            chat_id=settings.TELEGRAM_CHAT_ID
        )
        await self.telegram_bot.initialize()
        await self.telegram_bot.start()

        logger.info("All components initialized successfully")

    async def analyze_trade_history(self):
        """Phân tích lịch sử giao dịch và build strategy"""
        logger.info("Analyzing trade history...")

        try:
            # Lấy trade history (30 ngày gần nhất)
            end_time = int(datetime.now().timestamp() * 1000)
            start_time = int((datetime.now() - timedelta(days=30)).timestamp() * 1000)

            all_trades = []
            for symbol in settings.TRADING_PAIRS:
                trades = self.bingx_client.get_trade_history(
                    symbol=symbol,
                    start_time=start_time,
                    end_time=end_time
                )
                all_trades.extend(trades)

            if not all_trades:
                logger.warning("No trade history found. Using default strategy.")
                return None

            # Phân tích trades
            analyzer = TradeAnalyzer(all_trades)

            # Generate và gửi report
            report = analyzer.generate_report()
            logger.info("\n" + report)
            await self.telegram_bot.send_analysis_report(report)

            # Build analysis results
            analysis_results = {
                'summary_stats': analyzer.get_summary_stats(),
                'symbol_performance': analyzer.get_symbol_performance().to_dict('index'),
                'time_analysis': analyzer.get_time_based_analysis(),
                'patterns': analyzer.identify_patterns(),
            }

            # Initialize learned strategy
            self.strategy = LearnedStrategy(analysis_results)
            logger.info("Learned strategy initialized based on your trading history")

            return analysis_results

        except Exception as e:
            logger.error(f"Error analyzing trade history: {e}", exc_info=True)
            return None

    async def monitor_markets(self):
        """Monitor markets và generate signals"""
        logger.info("Starting market monitoring...")

        while self.is_running:
            try:
                for symbol in settings.TRADING_PAIRS:
                    # Get market data
                    klines = self.bingx_client.get_klines(
                        symbol=symbol,
                        interval=settings.DEFAULT_TIMEFRAME,
                        limit=200
                    )

                    if not klines:
                        continue

                    # Convert to DataFrame
                    df = pd.DataFrame(klines)

                    # Generate signal
                    signal = self.strategy.generate_signal(df)

                    if signal:
                        signal['symbol'] = symbol

                        # Check if should send
                        if self.signal_manager.should_send_signal(signal['symbol'], signal['side']):
                            # Send signal
                            await self.telegram_bot.send_signal(signal)
                            self.signal_manager.record_signal(signal)

                            logger.info(f"Signal sent: {signal['side']} {signal['symbol']}")

                # Wait before next check (5 minutes)
                await asyncio.sleep(300)

            except Exception as e:
                logger.error(f"Error in market monitoring: {e}", exc_info=True)
                await asyncio.sleep(60)

    async def start(self):
        """Start the bot"""
        try:
            await self.initialize()

            # Analyze trade history first
            await self.analyze_trade_history()

            # Start monitoring
            self.is_running = True
            logger.info("SignalA Bot started successfully!")
            logger.info(f"Monitoring pairs: {', '.join(settings.TRADING_PAIRS)}")
            logger.info(f"Timeframe: {settings.DEFAULT_TIMEFRAME}")

            await self.monitor_markets()

        except Exception as e:
            logger.error(f"Fatal error: {e}", exc_info=True)
            raise

    async def stop(self):
        """Stop the bot"""
        logger.info("Stopping SignalA Bot...")
        self.is_running = False

        if self.telegram_bot:
            await self.telegram_bot.stop()

        logger.info("Bot stopped")

async def main():
    """Main entry point"""
    bot = SignalABot()

    try:
        await bot.start()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        await bot.stop()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        await bot.stop()
        raise

if __name__ == "__main__":
    asyncio.run(main())
