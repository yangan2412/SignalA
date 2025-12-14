"""
Data-Driven SHORT Strategy
Based on analysis of 95 SHORT trades with 81.1% win rate
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, Optional
from .base_strategy import BaseStrategy

logger = logging.getLogger(__name__)


class DataDrivenShortStrategy(BaseStrategy):
    """
    Strategy based on historical SHORT trades analysis

    Key findings:
    - Win rate: 81.1% (77 wins, 18 losses)
    - Optimal leverage: 20-25x (25x has 93.3% win rate)
    - Optimal margin: $15-20 per trade
    - Best symbols: turbo, cake, the, portal, 1000bonk
    - TP levels: TP1 at -8%, TP2 at -13%
    - SL: +5% from entry
    """

    def __init__(self, enable_martingale: bool = True):
        super().__init__(name="Data-Driven SHORT Strategy")

        # From analysis
        self.optimal_leverage = 25
        self.optimal_margin = 20
        self.tp1_percent = 8  # -8% from entry
        self.tp2_percent = 13  # -13% from entry
        self.sl_percent = 5   # +5% from entry

        # Signal criteria
        self.rsi_overbought = 65
        self.min_confidence = 0.7

        # Symbol performance boosts (from analysis)
        self.symbol_boost = {
            'THE-USDT': 0.15,         # 100% win rate
            'PORTAL-USDT': 0.15,      # 100% win rate
            '1000000MOG-USDT': 0.15,  # 100% win rate
            'LISTA-USDT': 0.10,       # 100% win rate
            'TURBO-USDT': 0.10,       # 85.7% win rate
            'CAKE-USDT': 0.05,        # 75% win rate
            'XRP-USDT': 0.05,         # 75% win rate
            'BTC-USDT': 0.05,         # 75% win rate
            '1000BONK-USDT': 0.05,    # 75% win rate
        }

        # Martingale configuration (based on 90.5% win rate historical data)
        self.enable_martingale = enable_martingale
        self.max_martingale_steps = 5
        self.martingale_trigger_pct = 15.0  # Price move % to trigger next step
        self.step1_multiplier = 2.5         # Margin multiplier for first martingale
        self.step2_plus_multiplier = 1.35   # Margin multiplier for subsequent steps

        logger.info(
            f"Strategy initialized: martingale={'enabled' if enable_martingale else 'disabled'}"
        )

    def generate_signal(self, market_data: Dict) -> Optional[Dict]:
        """
        Generate SHORT signal based on technical indicators

        Args:
            market_data: Dict with 'symbol' and 'klines' (DataFrame)

        Returns:
            Signal dict or None
        """
        try:
            symbol = market_data['symbol']
            df = market_data['klines']

            # Validate data
            if len(df) < 200:
                logger.warning(f"{symbol}: Not enough data ({len(df)} candles)")
                return None

            # Calculate indicators
            rsi = self._calculate_rsi(df)
            macd, macd_signal = self._calculate_macd(df)
            ema50 = self._calculate_ema(df, period=50)

            current_price = float(df['close'].iloc[-1])

            # Check SHORT conditions
            conditions = {
                'rsi_overbought': rsi > self.rsi_overbought,
                'macd_bearish': macd < macd_signal,
                'macd_crossunder': self._check_macd_crossunder(df),
                'below_ema50': current_price < ema50,
            }

            # Calculate confidence (0-1)
            confidence = self._calculate_confidence(conditions, symbol)

            if confidence < self.min_confidence:
                logger.debug(f"{symbol}: Confidence too low ({confidence:.2f})")
                return None

            # Determine leverage and margin based on confidence
            if confidence >= 0.85:
                leverage = 25
                margin = 20
            elif confidence >= 0.7:
                leverage = 20
                margin = 15
            else:
                return None

            # Calculate TP/SL based on data analysis
            entry_price = current_price
            tp1 = entry_price * (1 - self.tp1_percent / 100)
            tp2 = entry_price * (1 - self.tp2_percent / 100)
            sl = entry_price * (1 + self.sl_percent / 100)

            signal = {
                'symbol': symbol,
                'side': 'SHORT',
                'entry_price': entry_price,
                'stop_loss': sl,
                'take_profit_1': tp1,
                'take_profit_2': tp2,
                'confidence': confidence,
                'strategy': self.name,
                'recommended_leverage': leverage,
                'recommended_margin': margin,
                'indicators': {
                    'rsi': round(rsi, 2),
                    'macd': round(macd, 4),
                    'macd_signal': round(macd_signal, 4),
                    'ema_50': round(ema50, 2),
                    'price': current_price
                }
            }

            # Add martingale fields if enabled
            if self.enable_martingale:
                signal['signal_type'] = 'INITIAL'
                signal['step_number'] = 1
                signal['max_steps'] = self.max_martingale_steps
                signal['trigger_percent'] = self.martingale_trigger_pct
                signal['step1_multiplier'] = self.step1_multiplier
                signal['step2_plus_multiplier'] = self.step2_plus_multiplier
                logger.info(
                    f"✅ {symbol} SHORT signal (INITIAL) generated "
                    f"(confidence: {confidence:.2f}, leverage: {leverage}x, "
                    f"martingale: enabled, max steps: {self.max_martingale_steps})"
                )
            else:
                signal['signal_type'] = 'STANDALONE'
                logger.info(
                    f"✅ {symbol} SHORT signal (STANDALONE) generated "
                    f"(confidence: {confidence:.2f}, leverage: {leverage}x)"
                )

            return signal

        except Exception as e:
            logger.error(f"Error generating signal for {symbol}: {e}", exc_info=True)
            return None

    def _calculate_confidence(self, conditions: Dict, symbol: str) -> float:
        """
        Calculate confidence score

        Args:
            conditions: Dict of boolean conditions
            symbol: Trading symbol

        Returns:
            Confidence score (0-1)
        """
        # Base confidence from conditions met
        conditions_met = sum(conditions.values())
        base_confidence = conditions_met / len(conditions)

        # Boost for high-performing symbols from analysis
        boost = self.symbol_boost.get(symbol, 0)

        # Final confidence (capped at 1.0)
        confidence = min(base_confidence + boost, 1.0)

        return confidence

    def _calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> float:
        """
        Calculate Relative Strength Index

        Args:
            df: DataFrame with 'close' prices
            period: RSI period (default 14)

        Returns:
            Current RSI value
        """
        close = df['close'].astype(float)

        # Calculate price changes
        delta = close.diff()

        # Separate gains and losses
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        # Calculate average gain and loss
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()

        # Calculate RS and RSI
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return float(rsi.iloc[-1])

    def _calculate_macd(self, df: pd.DataFrame,
                       fast=12, slow=26, signal=9) -> tuple:
        """
        Calculate MACD (Moving Average Convergence Divergence)

        Args:
            df: DataFrame with 'close' prices
            fast: Fast EMA period
            slow: Slow EMA period
            signal: Signal line period

        Returns:
            Tuple of (macd, signal_line)
        """
        close = df['close'].astype(float)

        # Calculate EMAs
        ema_fast = close.ewm(span=fast, adjust=False).mean()
        ema_slow = close.ewm(span=slow, adjust=False).mean()

        # MACD line
        macd_line = ema_fast - ema_slow

        # Signal line
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()

        return float(macd_line.iloc[-1]), float(signal_line.iloc[-1])

    def _calculate_ema(self, df: pd.DataFrame, period: int = 50) -> float:
        """
        Calculate Exponential Moving Average

        Args:
            df: DataFrame with 'close' prices
            period: EMA period

        Returns:
            Current EMA value
        """
        close = df['close'].astype(float)
        ema = close.ewm(span=period, adjust=False).mean()
        return float(ema.iloc[-1])

    def _check_macd_crossunder(self, df: pd.DataFrame) -> bool:
        """
        Check if MACD just crossed under signal line (bearish)

        Args:
            df: DataFrame with 'close' prices

        Returns:
            True if bearish crossunder occurred
        """
        try:
            close = df['close'].astype(float)

            # Calculate MACD for last 2 candles
            ema_fast = close.ewm(span=12, adjust=False).mean()
            ema_slow = close.ewm(span=26, adjust=False).mean()
            macd_line = ema_fast - ema_slow
            signal_line = macd_line.ewm(span=9, adjust=False).mean()

            # Check crossunder: prev MACD >= Signal, current MACD < Signal
            prev_macd = macd_line.iloc[-2]
            prev_signal = signal_line.iloc[-2]
            curr_macd = macd_line.iloc[-1]
            curr_signal = signal_line.iloc[-1]

            crossunder = (prev_macd >= prev_signal) and (curr_macd < curr_signal)

            return crossunder

        except:
            return False
