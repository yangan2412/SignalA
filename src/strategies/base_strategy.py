from abc import ABC, abstractmethod
from typing import Dict, List, Optional
import pandas as pd
import logging

logger = logging.getLogger(__name__)

class BaseStrategy(ABC):
    """Base class cho tất cả trading strategies"""

    def __init__(self, name: str, config: Optional[Dict] = None):
        self.name = name
        self.config = config or {}
        self.signals = []

    @abstractmethod
    def generate_signal(self, market_data: pd.DataFrame) -> Optional[Dict]:
        """
        Generate trading signal from market data

        Args:
            market_data: DataFrame with OHLCV data

        Returns:
            Signal dict or None if no signal
        """
        pass

    def validate_signal(self, signal: Dict) -> bool:
        """Validate signal before sending"""
        required_fields = ['symbol', 'side', 'entry_price', 'confidence']
        return all(field in signal for field in required_fields)

    def calculate_stop_loss(self, entry_price: float, side: str, atr: float = None) -> float:
        """
        Calculate stop loss level

        Args:
            entry_price: Entry price
            side: LONG or SHORT
            atr: Average True Range (optional)

        Returns:
            Stop loss price
        """
        # Default 2% stop loss
        default_sl_pct = self.config.get('stop_loss_pct', 0.02)

        if side == 'LONG':
            sl_price = entry_price * (1 - default_sl_pct)
        else:  # SHORT
            sl_price = entry_price * (1 + default_sl_pct)

        return round(sl_price, 2)

    def calculate_take_profit(self, entry_price: float, side: str,
                             risk_reward: float = 2.0) -> List[float]:
        """
        Calculate take profit levels

        Args:
            entry_price: Entry price
            side: LONG or SHORT
            risk_reward: Risk/reward ratio

        Returns:
            List of TP levels
        """
        default_sl_pct = self.config.get('stop_loss_pct', 0.02)
        tp_distance = default_sl_pct * risk_reward

        if side == 'LONG':
            tp1 = entry_price * (1 + tp_distance * 0.5)
            tp2 = entry_price * (1 + tp_distance)
        else:  # SHORT
            tp1 = entry_price * (1 - tp_distance * 0.5)
            tp2 = entry_price * (1 - tp_distance)

        return [round(tp1, 2), round(tp2, 2)]

    def format_signal(self, symbol: str, side: str, entry_price: float,
                     indicators: Dict, confidence: float = 0.7) -> Dict:
        """Format trading signal"""
        sl = self.calculate_stop_loss(entry_price, side)
        tp_levels = self.calculate_take_profit(entry_price, side)

        signal = {
            'symbol': symbol,
            'side': side,
            'entry_price': entry_price,
            'stop_loss': sl,
            'take_profit_1': tp_levels[0],
            'take_profit_2': tp_levels[1],
            'indicators': indicators,
            'confidence': confidence,
            'strategy': self.name,
        }

        return signal if self.validate_signal(signal) else None
