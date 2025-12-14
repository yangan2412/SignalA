#!/usr/bin/env python3
"""
Test script to verify all imports and basic functionality
"""

import sys

print("Testing imports...")
print("=" * 60)

try:
    print("✓ Importing config...")
    from config.settings import Settings

    print("✓ Importing BingX client...")
    from src.api.bingx_client import BingXClient

    print("✓ Importing SymbolSelector...")
    from src.api.symbol_selector import SymbolSelector

    print("✓ Importing DataDrivenShortStrategy...")
    from src.strategies.data_driven_short_strategy import DataDrivenShortStrategy

    print("✓ Importing DatabaseManager...")
    from src.database.db_manager import DatabaseManager

    print("✓ Importing SignalTracker...")
    from src.database.signal_tracker import SignalTracker

    print("✓ Importing TelegramBot...")
    from src.bot.telegram_bot import TradingSignalBot

    print("✓ Importing SignalManager...")
    from src.bot.signal_manager import SignalManager

    print("\n" + "=" * 60)
    print("✅ ALL IMPORTS SUCCESSFUL!")
    print("=" * 60)

    # Test basic initialization
    print("\nTesting basic initialization...")
    print("-" * 60)

    print("✓ Creating Settings instance...")
    settings = Settings()
    print(f"  - Symbol mode: {settings.SYMBOL_MODE}")
    print(f"  - Database URL: {settings.DATABASE_URL}")

    print("✓ Creating DataDrivenShortStrategy instance...")
    strategy = DataDrivenShortStrategy()
    print(f"  - Strategy name: {strategy.name}")
    print(f"  - Optimal leverage: {strategy.optimal_leverage}x")
    print(f"  - TP1: -{strategy.tp1_percent}%, TP2: -{strategy.tp2_percent}%")
    print(f"  - SL: +{strategy.sl_percent}%")

    print("\n" + "=" * 60)
    print("✅ ALL BASIC TESTS PASSED!")
    print("=" * 60)
    print("\nReady to run the bot!")
    print("\nNext steps:")
    print("1. Make sure you have set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env")
    print("2. Run: python main.py")

    sys.exit(0)

except ImportError as e:
    print(f"\n❌ Import error: {e}")
    print("\nMake sure all dependencies are installed:")
    print("  pip install --break-system-packages -r requirements.txt")
    sys.exit(1)
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
