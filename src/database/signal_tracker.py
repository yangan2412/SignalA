"""
Signal Tracker - Monitor active signals và update results
"""

import asyncio
import logging
from typing import List, Optional
from .db_manager import DatabaseManager
from ..api.bingx_client import BingXClient

logger = logging.getLogger(__name__)


class SignalTracker:
    """
    Track active signals và update kết quả khi hit TP/SL
    Also monitors position sequences for martingale opportunities
    """

    def __init__(self, db_manager: DatabaseManager, bingx_client: BingXClient,
                 telegram_bot=None, martingale_manager=None):
        self.db = db_manager
        self.bingx = bingx_client
        self.telegram = telegram_bot
        self.martingale = martingale_manager
        self.is_running = False

    async def start_tracking(self):
        """Start tracking loop"""
        self.is_running = True
        logger.info("Signal tracker started")

        while self.is_running:
            try:
                await self._check_all_active_signals()
                await asyncio.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Error in signal tracking: {e}", exc_info=True)
                await asyncio.sleep(60)

    async def _check_all_active_signals(self):
        """Check all active signals and sequences"""
        # Check individual signals (for STANDALONE signals)
        await self._check_individual_signals()

        # Check sequences for martingale triggers and TP/SL
        if self.martingale:
            await self._check_sequences_for_martingale()

    async def _check_individual_signals(self):
        """Check standalone signals (not part of martingale sequences)"""
        active_signals = self.db.get_active_signals()

        if not active_signals:
            return

        # Filter for standalone signals only (sequences are checked separately)
        standalone_signals = [s for s in active_signals if s.sequence_id is None]

        if not standalone_signals:
            return

        logger.info(f"Checking {len(standalone_signals)} standalone signals...")

        for signal in standalone_signals:
            try:
                # Get current price
                ticker = self.bingx.get_ticker_price(signal.symbol)

                if not ticker:
                    continue

                # Parse price based on response format
                if isinstance(ticker, dict):
                    if 'price' in ticker:
                        current_price = float(ticker['price'])
                    elif 'lastPrice' in ticker:
                        current_price = float(ticker['lastPrice'])
                    else:
                        logger.warning(f"Cannot parse price from ticker: {ticker}")
                        continue
                else:
                    logger.warning(f"Unexpected ticker format: {ticker}")
                    continue

                # Store old status before update
                old_status = signal.status

                # Update price and check outcome
                self.db.update_signal_price(signal.id, current_price)

                # Refresh signal to get updated status
                updated_signal = self.db.get_signal_by_id(signal.id)

                # If status changed from ACTIVE to CLOSED, send Telegram notification
                if old_status == 'ACTIVE' and updated_signal and updated_signal.status == 'CLOSED':
                    logger.info(f"Signal {signal.id} closed: {signal.symbol}")
                    await self._send_signal_closed_notification(updated_signal)

                logger.debug(f"Updated signal {signal.id}: {signal.symbol} @ {current_price}")

            except Exception as e:
                logger.error(f"Error checking signal {signal.id}: {e}")

    async def _check_sequences_for_martingale(self):
        """Check active sequences for martingale triggers and TP/SL hits"""
        active_sequences = self.db.get_active_sequences()

        if not active_sequences:
            return

        logger.info(f"Checking {len(active_sequences)} active sequences...")

        for sequence in active_sequences:
            try:
                # Get current price
                ticker = self.bingx.get_ticker_price(sequence.symbol)

                if not ticker:
                    continue

                # Parse price
                if isinstance(ticker, dict):
                    if 'price' in ticker:
                        current_price = float(ticker['price'])
                    elif 'lastPrice' in ticker:
                        current_price = float(ticker['lastPrice'])
                    else:
                        logger.warning(f"Cannot parse price from ticker: {ticker}")
                        continue
                else:
                    logger.warning(f"Unexpected ticker format: {ticker}")
                    continue

                # Check if TP/SL hit
                should_close, outcome = self.martingale.check_sequence_close(sequence, current_price)
                if should_close:
                    logger.info(f"Sequence {sequence.id} hit {outcome}: {sequence.symbol} @ {current_price}")
                    # Close sequence
                    closed_sequence = self.db.close_sequence(sequence.id, current_price, outcome)
                    # Send notification
                    await self._send_sequence_closed_notification(closed_sequence)
                    continue

                # Check if martingale should be suggested
                should_add, suggestion = self.martingale.should_add_martingale(sequence, current_price)
                if should_add:
                    logger.info(
                        f"Martingale trigger for sequence {sequence.id}: "
                        f"{sequence.symbol} moved {suggestion['price_move_pct']:+.2f}%"
                    )
                    # Update suggestion time to prevent spam
                    self.db.update_sequence_martingale_suggestion_time(sequence.id)
                    # Send suggestion
                    await self._send_martingale_suggestion(sequence, suggestion)

                logger.debug(f"Checked sequence {sequence.id}: {sequence.symbol} @ {current_price}")

            except Exception as e:
                logger.error(f"Error checking sequence {sequence.id}: {e}", exc_info=True)

    async def _send_martingale_suggestion(self, sequence, suggestion):
        """Send Telegram notification for martingale opportunity"""
        if not self.telegram:
            logger.debug("No Telegram bot configured, skipping martingale suggestion")
            return

        try:
            message = f"""
🔔 <b>MARTINGALE SUGGESTION - {suggestion['symbol']}</b>

📊 <b>Sequence Info:</b>
  • Sequence ID: {suggestion['sequence_id']}
  • Current Step: {suggestion['current_step']}/{suggestion['max_steps']}
  • Direction: {suggestion['direction']}

📈 <b>Price Movement:</b>
  • Last Entry: ${suggestion['last_entry_price']:.6f}
  • Current Price: ${suggestion['current_price']:.6f}
  • Price Move: {suggestion['price_move_pct']:+.2f}% (trigger: {suggestion['trigger_percent']:+.2f}%)

💡 <b>SUGGESTION:</b>
  • Suggested Entry: ${suggestion['suggested_entry']:.6f}
  • Add Margin: ${suggestion['suggested_margin']:.2f}
  • Step: {suggestion['next_step']}/{suggestion['max_steps']}

📊 <b>CURRENT TARGETS:</b>
  • Weighted Avg: ${suggestion['current_weighted_avg']:.6f}
  • TP1: ${suggestion['current_tp1']:.6f}
  • TP2: ${suggestion['current_tp2']:.6f}
  • Total Margin: ${suggestion['current_total_margin']:.2f}

🎯 <b>NEW TARGETS (After Adding):</b>
  • New Weighted Avg: ${suggestion['new_weighted_avg']:.6f}
  • New TP1: ${suggestion['new_tp1']:.6f}
  • New TP2: ${suggestion['new_tp2']:.6f}
  • New Total Margin: ${suggestion['new_total_margin']:.2f}

⚠️ <b>Action Required:</b>
This is a suggestion only. To add martingale entry:
1. Manually enter position at suggested price
2. Use suggested margin amount
3. Monitor for TP/SL based on NEW weighted average

<i>Weighted average calculation ensures optimal risk/reward</i>
"""

            await self.telegram.send_message(message)
            logger.info(f"Sent martingale suggestion for sequence {sequence.id}")

        except Exception as e:
            logger.error(f"Error sending martingale suggestion: {e}", exc_info=True)

    async def _send_sequence_closed_notification(self, sequence):
        """Send Telegram notification when sequence closes"""
        if not self.telegram:
            logger.debug("No Telegram bot configured, skipping notification")
            return

        try:
            # Outcome emojis
            outcome_emoji = {
                'HIT_TP1': '🎯',
                'HIT_TP2': '🎯🎯',
                'HIT_SL': '❌',
                'EXPIRED': '⏰'
            }

            emoji = outcome_emoji.get(sequence.status.value.replace('CLOSED_', ''), '✅')

            # Format PnL with color
            pnl_sign = '+' if sequence.total_pnl >= 0 else ''

            message = f"""
{emoji} <b>SEQUENCE CLOSED - {sequence.symbol}</b>

📊 <b>Result:</b> {sequence.status.value}
🔢 <b>Steps Completed:</b> {sequence.current_step}/{sequence.max_steps}

💰 <b>Entry Details:</b>
  • First Entry: ${sequence.first_entry_price:.6f}
  • Last Entry: ${sequence.last_entry_price:.6f}
  • Weighted Avg Entry: ${sequence.weighted_avg_entry:.6f}

💰 <b>Exit:</b> ${sequence.final_exit_price:.6f}

📈 <b>Total PnL:</b> ${pnl_sign}{sequence.total_pnl:.2f} ({pnl_sign}{sequence.total_pnl_pct:.2f}%)

💼 <b>Position Details:</b>
  • Total Margin: ${sequence.total_margin:.2f}
  • Leverage: {sequence.total_leverage:.0f}x
  • PnL per Step: ${sequence.total_pnl / sequence.current_step:.2f}

⏱ <b>Duration:</b> {(sequence.closed_at - sequence.opened_at).total_seconds() / 3600:.1f} hours
🤖 <b>Strategy:</b> {sequence.strategy_name}

<i>PnL calculated from weighted average entry: ${sequence.weighted_avg_entry:.6f}</i>
"""

            await self.telegram.send_message(message)
            logger.info(f"Sent close notification for sequence {sequence.id}")

        except Exception as e:
            logger.error(f"Error sending sequence close notification: {e}", exc_info=True)

    def stop_tracking(self):
        """Stop tracking"""
        self.is_running = False
        logger.info("Signal tracker stopped")

    async def track_signal_manual(self, signal_id: int, current_price: float):
        """Manually update a signal (for testing)"""
        self.db.update_signal_price(signal_id, current_price)
        logger.info(f"Manually updated signal {signal_id} with price {current_price}")

    async def _send_signal_closed_notification(self, signal):
        """Send Telegram notification when signal closes"""
        if not self.telegram:
            logger.debug("No Telegram bot configured, skipping notification")
            return

        try:
            result = signal.result
            if not result:
                logger.warning(f"Signal {signal.id} has no result record")
                return

            # Outcome emojis
            outcome_emoji = {
                'HIT_TP1': '🎯',
                'HIT_TP2': '🎯🎯',
                'HIT_SL': '❌',
                'EXPIRED': '⏰'
            }

            emoji = outcome_emoji.get(result.outcome, '✅')

            # Format PnL with color
            pnl_sign = '+' if result.theoretical_pnl >= 0 else ''

            message = f"""
{emoji} <b>SIGNAL CLOSED - {signal.symbol}</b>

📊 <b>Result:</b> {result.outcome}
💰 <b>Entry:</b> ${signal.entry_price:.6f}
💰 <b>Exit:</b> ${result.actual_exit_price:.6f}
📈 <b>PnL:</b> ${pnl_sign}{result.theoretical_pnl:.2f} ({pnl_sign}{result.theoretical_pnl_pct:.2f}%)

⏱ <b>Duration:</b> {result.duration_hours:.1f} hours
🤖 <b>Strategy:</b> {signal.strategy_name}
"""

            await self.telegram.send_message(message)
            logger.info(f"Sent close notification for signal {signal.id}")

        except Exception as e:
            logger.error(f"Error sending close notification: {e}", exc_info=True)
