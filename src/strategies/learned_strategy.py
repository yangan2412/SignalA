import pandas as pd
import pandas_ta as ta
from typing import Dict, Optional
import logging
from .base_strategy import BaseStrategy

logger = logging.getLogger(__name__)

class LearnedStrategy(BaseStrategy):
    """
    Strategy được học từ trade history của user
    Tự động điều chỉnh dựa trên patterns đã phân tích
    """

    def __init__(self, analysis_results: Dict, config: Optional[Dict] = None):
        super().__init__("Learned Strategy", config)
        self.analysis = analysis_results
        self.best_hours = analysis_results.get('time_analysis', {}).get('best_trading_hours', [])
        self.best_symbols = self._get_best_symbols()
        self.preferred_direction = self._get_preferred_direction()

    def _get_best_symbols(self) -> list:
        """Lấy các symbol có performance tốt nhất"""
        symbol_perf = self.analysis.get('symbol_performance', {})
        if not symbol_perf:
            return []

        # Sort by win rate và total profit
        sorted_symbols = sorted(
            symbol_perf.items(),
            key=lambda x: (x[1].get('win_rate', 0), x[1].get('total_profit', 0)),
            reverse=True
        )

        return [symbol for symbol, _ in sorted_symbols[:5]]  # Top 5 symbols

    def _get_preferred_direction(self) -> str:
        """Xác định hướng giao dịch ưu tiên (LONG/SHORT)"""
        summary = self.analysis.get('summary_stats', {})
        long_pct = summary.get('long_percentage', 50)

        # Nếu user có xu hướng LONG > 60% thì ưu tiên LONG
        if long_pct > 60:
            return 'LONG'
        elif long_pct < 40:
            return 'SHORT'
        else:
            return 'BOTH'

    def generate_signal(self, market_data: pd.DataFrame) -> Optional[Dict]:
        """
        Generate signal dựa trên learned patterns

        Args:
            market_data: DataFrame with columns [time, open, high, low, close, volume]

        Returns:
            Trading signal or None
        """
        if market_data.empty or len(market_data) < 50:
            return None

        # Ensure required columns
        df = market_data.copy()
        df.columns = ['time', 'open', 'high', 'low', 'close', 'volume']

        # Convert to numeric
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        # Calculate indicators
        df['rsi'] = ta.rsi(df['close'], length=14)
        df['macd'] = ta.macd(df['close'])['MACD_12_26_9']
        df['macd_signal'] = ta.macd(df['close'])['MACDs_12_26_9']
        df['ema_50'] = ta.ema(df['close'], length=50)
        df['ema_200'] = ta.ema(df['close'], length=200)

        # Get latest values
        latest = df.iloc[-1]
        prev = df.iloc[-2]

        # Check if it's good trading hour
        current_hour = pd.Timestamp.now().hour
        is_good_hour = current_hour in self.best_hours if self.best_hours else True

        # Generate signal based on learned preferences
        signal = self._evaluate_conditions(latest, prev, is_good_hour)

        return signal

    def _evaluate_conditions(self, latest: pd.Series, prev: pd.Series, is_good_hour: bool) -> Optional[Dict]:
        """Đánh giá điều kiện và tạo signal"""

        # LONG conditions
        long_conditions = [
            latest['rsi'] < 35,  # Oversold
            latest['macd'] > latest['macd_signal'] and prev['macd'] <= prev['macd_signal'],  # MACD crossover
            latest['close'] > latest['ema_50'],  # Price above EMA 50
            is_good_hour,
        ]

        # SHORT conditions
        short_conditions = [
            latest['rsi'] > 65,  # Overbought
            latest['macd'] < latest['macd_signal'] and prev['macd'] >= prev['macd_signal'],  # MACD crossunder
            latest['close'] < latest['ema_50'],  # Price below EMA 50
            is_good_hour,
        ]

        # Count true conditions
        long_score = sum(long_conditions) / len(long_conditions)
        short_score = sum(short_conditions) / len(short_conditions)

        # Điều chỉnh theo preferred direction
        if self.preferred_direction == 'LONG':
            long_score *= 1.2
        elif self.preferred_direction == 'SHORT':
            short_score *= 1.2

        # Threshold từ analysis
        threshold = self.analysis.get('summary_stats', {}).get('win_rate', 50) / 100

        # Generate signal
        if long_score >= threshold and long_score > short_score:
            return self._create_long_signal(latest, long_score)
        elif short_score >= threshold and short_score > long_score:
            return self._create_short_signal(latest, short_score)

        return None

    def _create_long_signal(self, latest: pd.Series, confidence: float) -> Dict:
        """Tạo LONG signal"""
        entry_price = float(latest['close'])

        indicators = {
            'RSI': f"{latest['rsi']:.1f} (oversold)",
            'MACD': "Bullish crossover",
            'Price': f"Above EMA 50 (${latest['ema_50']:.2f})",
        }

        return self.format_signal(
            symbol="BTC-USDT",  # TODO: Dynamic symbol
            side="LONG",
            entry_price=entry_price,
            indicators=indicators,
            confidence=confidence
        )

    def _create_short_signal(self, latest: pd.Series, confidence: float) -> Dict:
        """Tạo SHORT signal"""
        entry_price = float(latest['close'])

        indicators = {
            'RSI': f"{latest['rsi']:.1f} (overbought)",
            'MACD': "Bearish crossunder",
            'Price': f"Below EMA 50 (${latest['ema_50']:.2f})",
        }

        return self.format_signal(
            symbol="BTC-USDT",
            side="SHORT",
            entry_price=entry_price,
            indicators=indicators,
            confidence=confidence
        )
