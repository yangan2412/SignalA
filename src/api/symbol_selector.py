"""
Symbol Selector - Choose trading pairs for signal generation
"""

import logging
from typing import List
from .bingx_client import BingXClient

logger = logging.getLogger(__name__)


class SymbolSelector:
    """
    Select trading symbols using two modes:
    1. Whitelist: Fixed list of high-performing symbols from analysis
    2. Volatility: Dynamic selection based on 24h price movement
    """

    def __init__(self, bingx_client: BingXClient, mode='whitelist',
                 top_n=20, min_volume=1000000):
        """
        Initialize symbol selector

        Args:
            bingx_client: BingX API client
            mode: 'whitelist' or 'volatility'
            top_n: Number of symbols to return in volatility mode
            min_volume: Minimum 24h volume filter (USDT)
        """
        self.bingx = bingx_client
        self.mode = mode
        self.top_n = top_n
        self.min_volume = min_volume

        # Whitelist from historical analysis (95 SHORT trades, 81.1% win rate)
        # Symbols normalized to BingX format (SYMBOL-USDT)
        self.whitelist = [
            'TURBO-USDT',    # 85.7% win rate, $90.19 avg profit
            'CAKE-USDT',     # 75.0% win rate, $128.66 avg profit
            'THE-USDT',      # 100% win rate, $129.58 avg profit
            'PORTAL-USDT',   # 100% win rate, $127.89 avg profit
            '1000BONK-USDT', # 75.0% win rate, $77.90 avg profit
            'XRP-USDT',      # 75.0% win rate, $32.63 avg profit
            'BTC-USDT',      # 75.0% win rate, $10.17 avg profit
        ]

    def get_symbols(self) -> List[str]:
        """
        Get list of symbols to scan based on mode

        Returns:
            List of symbol strings (e.g., ['BTC-USDT', 'ETH-USDT'])
        """
        if self.mode == 'whitelist':
            logger.info(f"Using whitelist mode: {len(self.whitelist)} symbols")
            return self.whitelist.copy()
        elif self.mode == 'volatility':
            return self._get_volatile_symbols()
        else:
            logger.warning(f"Unknown mode '{self.mode}', fallback to whitelist")
            return self.whitelist.copy()

    def _get_volatile_symbols(self) -> List[str]:
        """
        Get symbols with highest 24h volatility

        Returns:
            List of top N most volatile symbols
        """
        try:
            logger.info("Fetching 24hr ticker data...")
            tickers = self.bingx.get_24hr_tickers()

            if not tickers:
                logger.warning("No ticker data received, fallback to whitelist")
                return self.whitelist.copy()

            # Filter and sort tickers
            filtered_tickers = []

            for ticker in tickers:
                # Parse fields (handle different API response formats)
                symbol = ticker.get('symbol', '')
                price_change_pct = float(ticker.get('priceChangePercent', 0))
                volume = float(ticker.get('volume', 0))
                quote_volume = float(ticker.get('quoteVolume', volume))  # volume in USDT

                # Skip if missing data
                if not symbol or price_change_pct == 0:
                    continue

                # Filter by volume (use quote volume which is in USDT)
                if quote_volume < self.min_volume:
                    continue

                # Filter to only USDT pairs
                if not symbol.endswith('-USDT'):
                    continue

                filtered_tickers.append({
                    'symbol': symbol,
                    'volatility': abs(price_change_pct),
                    'price_change_pct': price_change_pct,
                    'volume': quote_volume
                })

            # Sort by volatility (descending)
            filtered_tickers.sort(key=lambda x: x['volatility'], reverse=True)

            # Get top N
            top_symbols = [t['symbol'] for t in filtered_tickers[:self.top_n]]

            logger.info(f"Selected {len(top_symbols)} volatile symbols (from {len(filtered_tickers)} candidates)")
            if top_symbols:
                logger.info(f"Top 5: {top_symbols[:5]}")

            # Fallback to whitelist if no symbols found
            if not top_symbols:
                logger.warning("No symbols meet volatility criteria, fallback to whitelist")
                return self.whitelist.copy()

            return top_symbols

        except Exception as e:
            logger.error(f"Error getting volatile symbols: {e}", exc_info=True)
            logger.warning("Fallback to whitelist mode due to error")
            return self.whitelist.copy()
