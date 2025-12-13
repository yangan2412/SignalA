import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class SignalManager:
    """Quản lý signals và tránh spam"""

    def __init__(self, cooldown_minutes: int = 30):
        self.cooldown_minutes = cooldown_minutes
        self.sent_signals = {}  # symbol -> last_signal_time
        self.signal_history = []

    def should_send_signal(self, symbol: str, side: str) -> bool:
        """
        Kiểm tra xem có nên gửi signal không

        Args:
            symbol: Trading pair
            side: LONG or SHORT

        Returns:
            True if should send, False otherwise
        """
        key = f"{symbol}_{side}"
        last_signal_time = self.sent_signals.get(key)

        if last_signal_time is None:
            return True

        # Check cooldown period
        time_diff = datetime.now() - last_signal_time
        if time_diff > timedelta(minutes=self.cooldown_minutes):
            return True

        logger.info(f"Signal cooldown active for {key}. Last signal: {last_signal_time}")
        return False

    def record_signal(self, signal: Dict):
        """Record sent signal"""
        symbol = signal['symbol']
        side = signal['side']
        key = f"{symbol}_{side}"

        self.sent_signals[key] = datetime.now()
        self.signal_history.append({
            'time': datetime.now(),
            'signal': signal
        })

        # Keep only last 100 signals
        if len(self.signal_history) > 100:
            self.signal_history = self.signal_history[-100:]

    def get_signal_stats(self) -> Dict:
        """Get statistics about sent signals"""
        total_signals = len(self.signal_history)
        if total_signals == 0:
            return {
                'total_signals': 0,
                'signals_today': 0,
                'long_signals': 0,
                'short_signals': 0,
            }

        today = datetime.now().date()
        signals_today = sum(1 for s in self.signal_history if s['time'].date() == today)

        long_signals = sum(1 for s in self.signal_history if s['signal']['side'] == 'LONG')
        short_signals = total_signals - long_signals

        return {
            'total_signals': total_signals,
            'signals_today': signals_today,
            'long_signals': long_signals,
            'short_signals': short_signals,
        }
