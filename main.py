#!/usr/bin/env python3
"""
SignalA - Telegram Trading Signal Bot
Generate SHORT signals based on historical analysis (81.1% win rate)
"""

import asyncio
import logging
import pandas as pd
import os
from pathlib import Path

from config.settings import Settings
from src.api.bingx_client import BingXClient
from src.api.symbol_selector import SymbolSelector
from src.strategies.data_driven_short_strategy import DataDrivenShortStrategy
from src.strategies.martingale_manager import MartingaleManager
from src.bot.telegram_bot import TradingSignalBot
from src.bot.signal_manager import SignalManager
from src.database.db_manager import DatabaseManager
from src.database.signal_tracker import SignalTracker

# Configure logging
Path('logs').mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/bot.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class SignalABot:
    """Main bot orchestrator for SHORT signal generation"""

    def __init__(self):
        self.settings = Settings()
        self.bingx_client = None
        self.telegram_bot = None
        self.db = None
        self.symbol_selector = None
        self.strategy = None
        self.martingale_manager = None
        self.signal_manager = SignalManager(cooldown_minutes=30)
        self.signal_tracker = None
        self.is_running = False

    async def initialize(self):
        """Initialize all components"""
        logger.info("=" * 80)
        logger.info("  🤖 SIGNALA BOT - SHORT Signal Generator")
        logger.info("=" * 80)
        logger.info("")

        # Validate settings
        self.settings.validate()

        # Initialize BingX client
        logger.info("📡 Connecting to BingX API...")
        self.bingx_client = BingXClient(
            api_key=self.settings.BINGX_API_KEY,
            secret_key=self.settings.BINGX_SECRET_KEY,
            base_url=self.settings.BINGX_BASE_URL
        )

        if not self.bingx_client.test_connection():
            raise Exception("Failed to connect to BingX API")
        logger.info("✅ BingX API connected")

        # Initialize Database
        logger.info("🗄️  Initializing database...")
        self.db = DatabaseManager(self.settings.DATABASE_URL)
        logger.info("✅ Database initialized")

        # Initialize Telegram bot
        logger.info("📱 Starting Telegram bot...")
        self.telegram_bot = TradingSignalBot(
            bot_token=self.settings.TELEGRAM_BOT_TOKEN,
            chat_id=self.settings.TELEGRAM_CHAT_ID
        )
        await self.telegram_bot.initialize()
        await self.telegram_bot.start()
        logger.info("✅ Telegram bot started")

        # Initialize Symbol Selector
        symbol_mode = os.getenv('SYMBOL_MODE', 'whitelist')
        top_n = int(os.getenv('VOLATILITY_TOP_N', '20'))
        min_volume = float(os.getenv('VOLATILITY_MIN_VOLUME', '1000000'))

        logger.info(f"🎯 Symbol selection mode: {symbol_mode.upper()}")
        self.symbol_selector = SymbolSelector(
            bingx_client=self.bingx_client,
            mode=symbol_mode,
            top_n=top_n,
            min_volume=min_volume
        )

        # Initialize Data-Driven SHORT Strategy
        logger.info("📊 Loading Data-Driven SHORT Strategy...")
        enable_martingale = os.getenv('ENABLE_MARTINGALE', 'true').lower() == 'true'
        self.strategy = DataDrivenShortStrategy(enable_martingale=enable_martingale)
        logger.info(f"✅ Strategy loaded (based on 95 trades, 81.1% win rate, martingale: {enable_martingale})")

        # Initialize Martingale Manager
        if enable_martingale:
            logger.info("🎲 Initializing Martingale Manager...")
            max_steps = int(os.getenv('MARTINGALE_MAX_STEPS', '5'))
            trigger_pct = float(os.getenv('MARTINGALE_TRIGGER_PCT', '15.0'))
            self.martingale_manager = MartingaleManager(
                max_steps=max_steps,
                trigger_percent=trigger_pct,
                step1_multiplier=2.5,
                step2_plus_multiplier=1.35,
                tp1_percent=10.0,
                tp2_percent=15.0,
                cooldown_minutes=30
            )
            logger.info(f"✅ Martingale Manager initialized (max steps: {max_steps}, trigger: {trigger_pct}%)")

        # Initialize Signal Tracker
        logger.info("👁️  Starting signal tracker...")
        self.signal_tracker = SignalTracker(
            db_manager=self.db,
            bingx_client=self.bingx_client,
            telegram_bot=self.telegram_bot,
            martingale_manager=self.martingale_manager
        )
        # Start tracker in background
        asyncio.create_task(self.signal_tracker.start_tracking())
        logger.info("✅ Signal tracker started (monitoring every 60s)")

        logger.info("")
        logger.info("=" * 80)
        logger.info("  ✅ ALL COMPONENTS INITIALIZED SUCCESSFULLY")
        logger.info("=" * 80)
        logger.info("")

    async def monitor_markets(self):
        """Monitor markets và generate SHORT signals"""
        logger.info("🔍 Starting market monitoring...")
        logger.info("")

        while self.is_running:
            try:
                # Get symbols to scan
                symbols = self.symbol_selector.get_symbols()
                logger.info(f"📊 Scanning {len(symbols)} symbols for SHORT opportunities...")

                for symbol in symbols:
                    try:
                        # Get 4h klines (200 candles)
                        klines = self.bingx_client.get_klines(
                            symbol=symbol,
                            interval='4h',
                            limit=200
                        )

                        if not klines:
                            logger.debug(f"{symbol}: No kline data")
                            continue

                        # Convert to DataFrame
                        df = pd.DataFrame(klines)
                        df['close'] = df['close'].astype(float)
                        df['high'] = df['high'].astype(float)
                        df['low'] = df['low'].astype(float)
                        df['open'] = df['open'].astype(float)

                        # Prepare market data
                        market_data = {
                            'symbol': symbol,
                            'klines': df
                        }

                        # Generate signal
                        signal = self.strategy.generate_signal(market_data)

                        if not signal:
                            continue

                        # Check cooldown
                        if not self.signal_manager.should_send_signal(symbol, signal['side']):
                            logger.info(f"⏸️  {symbol} SHORT - cooldown active, skipping")
                            continue

                        # Create position sequence if martingale enabled
                        sequence_id = None
                        if signal.get('signal_type') == 'INITIAL':
                            logger.info(f"🎲 Creating position sequence for {symbol}...")
                            sequence = self.db.create_sequence(signal)
                            sequence_id = sequence.id
                            logger.info(f"✅ Sequence created (ID: {sequence_id}, max steps: {sequence.max_steps})")

                        # Save signal to database
                        logger.info(f"💾 Saving {symbol} SHORT signal to database...")
                        db_signal = self.db.create_signal(signal, sequence_id=sequence_id)
                        signal['id'] = db_signal.id

                        # Send to Telegram
                        logger.info(f"📤 Sending {symbol} SHORT signal to Telegram...")
                        await self.telegram_bot.send_signal(signal)

                        # Record in signal manager
                        self.signal_manager.record_signal(signal)

                        signal_type = signal.get('signal_type', 'STANDALONE')
                        logger.info(
                            f"✅ {symbol} SHORT signal sent "
                            f"(ID: {db_signal.id}, type: {signal_type}, "
                            f"confidence: {signal['confidence']:.2f}, "
                            f"leverage: {signal['recommended_leverage']}x)"
                        )
                        if sequence_id:
                            logger.info(f"   📊 Sequence ID: {sequence_id} (will monitor for martingale triggers)")
                        logger.info("")

                        # Small delay between symbols to avoid rate limits
                        await asyncio.sleep(2)

                    except Exception as e:
                        logger.error(f"Error processing {symbol}: {e}")
                        continue

                # Wait 5 minutes before next scan
                logger.info("⏰ Waiting 5 minutes before next scan...")
                logger.info("")
                await asyncio.sleep(300)

            except Exception as e:
                logger.error(f"Error in market monitoring: {e}", exc_info=True)
                await asyncio.sleep(60)

    async def start(self):
        """Start the bot"""
        try:
            await self.initialize()

            # Send startup message
            martingale_status = "✅ Enabled (90.5% win rate)" if self.strategy.enable_martingale else "❌ Disabled"
            startup_msg = f"""
🚀 <b>SignalA Bot Started!</b>

📊 <b>Strategy:</b> Data-Driven SHORT
📈 <b>Single Trade Win Rate:</b> 81.1%
🎲 <b>Martingale Mode:</b> {martingale_status}
🎯 <b>Leverage:</b> 20-25x
💰 <b>Margin:</b> $15-20 per signal

Bot is now scanning markets for HIGH-PROBABILITY SHORT signals every 5 minutes.

<i>Martingale sequences track weighted average entry for optimal TP calculation</i>
"""
            await self.telegram_bot.send_message(startup_msg)

            # Start monitoring
            self.is_running = True
            await self.monitor_markets()

        except Exception as e:
            logger.error(f"Fatal error: {e}", exc_info=True)
            raise

    async def stop(self):
        """Stop the bot"""
        logger.info("Stopping SignalA Bot...")
        self.is_running = False

        if self.signal_tracker:
            self.signal_tracker.stop_tracking()

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
