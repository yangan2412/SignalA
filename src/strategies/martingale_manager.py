"""
Martingale Manager - Core logic for weighted average and position sequencing

This module implements the martingale (gấp vốn) strategy based on analysis of
95 historical trades showing 90.5% win rate for martingale sequences.

Key principles:
- Trigger at +15% price movement (conservative)
- Margin progression: 2.5x for step 1, then 1.35x for subsequent steps
- TP/SL calculated from WEIGHTED AVERAGE entry (NOT first entry)
- Max 5 steps to prevent runaway losses
"""

from typing import Dict, Tuple, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class MartingaleManager:
    """Manages martingale position sequences and calculations"""

    def __init__(
        self,
        max_steps: int = 5,
        trigger_percent: float = 15.0,
        step1_multiplier: float = 2.5,
        step2_plus_multiplier: float = 1.35,
        tp1_percent: float = 10.0,
        tp2_percent: float = 15.0,
        cooldown_minutes: int = 30
    ):
        """
        Initialize MartingaleManager

        Args:
            max_steps: Maximum martingale steps (default: 5)
            trigger_percent: Price move % to trigger next step (default: 15%)
            step1_multiplier: Margin multiplier for first martingale (default: 2.5)
            step2_plus_multiplier: Margin multiplier for step 2+ (default: 1.35)
            tp1_percent: TP1 distance from weighted avg (default: 10%)
            tp2_percent: TP2 distance from weighted avg (default: 15%)
            cooldown_minutes: Cooldown between suggestions (default: 30 min)
        """
        self.max_steps = max_steps
        self.trigger_percent = trigger_percent
        self.step1_multiplier = step1_multiplier
        self.step2_plus_multiplier = step2_plus_multiplier
        self.tp1_percent = tp1_percent
        self.tp2_percent = tp2_percent
        self.cooldown_minutes = cooldown_minutes

        logger.info(
            f"MartingaleManager initialized: max_steps={max_steps}, "
            f"trigger={trigger_percent}%, step1={step1_multiplier}x, "
            f"step2+={step2_plus_multiplier}x"
        )

    def should_add_martingale(
        self,
        sequence,
        current_price: float
    ) -> Tuple[bool, Dict]:
        """
        Check if price has moved enough to trigger martingale suggestion

        Args:
            sequence: PositionSequence object
            current_price: Current market price

        Returns:
            (should_add, suggestion_dict) where:
            - should_add: Boolean indicating if martingale should be added
            - suggestion_dict: Details about the suggested martingale entry
        """
        # Check if sequence is still active
        if sequence.status.value != 'ACTIVE':
            return False, {}

        # Check if we've hit max steps
        if sequence.current_step >= self.max_steps:
            logger.debug(f"Sequence {sequence.id} at max steps ({self.max_steps})")
            return False, {}

        # Check cooldown to prevent spam suggestions
        if sequence.last_martingale_suggestion_at:
            time_since_last = datetime.utcnow() - sequence.last_martingale_suggestion_at
            if time_since_last < timedelta(minutes=self.cooldown_minutes):
                logger.debug(
                    f"Sequence {sequence.id} in cooldown "
                    f"({time_since_last.total_seconds()/60:.1f}min ago)"
                )
                return False, {}

        # Calculate price movement from last entry
        last_entry = sequence.last_entry_price or sequence.first_entry_price
        price_move_pct = self._calculate_price_move_pct(
            last_entry, current_price, sequence.direction.value
        )

        # Check if trigger threshold is met
        if price_move_pct < self.trigger_percent:
            return False, {}

        # Calculate suggestion details
        next_step = sequence.current_step + 1
        suggested_margin = self._calculate_next_margin(sequence)
        new_weighted_avg = self._calculate_new_weighted_avg(
            sequence, current_price, suggested_margin
        )
        new_tp1, new_tp2 = self._calculate_new_tps(
            new_weighted_avg, sequence.direction.value
        )

        suggestion = {
            'sequence_id': sequence.id,
            'current_step': sequence.current_step,
            'next_step': next_step,
            'max_steps': sequence.max_steps,
            'symbol': sequence.symbol,
            'direction': sequence.direction.value,
            'last_entry_price': last_entry,
            'current_price': current_price,
            'price_move_pct': price_move_pct,
            'trigger_percent': self.trigger_percent,
            'suggested_entry': current_price,
            'suggested_margin': suggested_margin,
            'current_weighted_avg': sequence.weighted_avg_entry,
            'new_weighted_avg': new_weighted_avg,
            'current_total_margin': sequence.total_margin,
            'new_total_margin': sequence.total_margin + suggested_margin,
            'current_tp1': sequence.current_tp1,
            'current_tp2': sequence.current_tp2,
            'new_tp1': new_tp1,
            'new_tp2': new_tp2,
        }

        logger.info(
            f"🔔 Martingale trigger for {sequence.symbol} sequence {sequence.id}: "
            f"Step {next_step}/{self.max_steps}, "
            f"Price moved {price_move_pct:+.2f}% (trigger: {self.trigger_percent}%)"
        )

        return True, suggestion

    def _calculate_price_move_pct(
        self,
        entry_price: float,
        current_price: float,
        direction: str
    ) -> float:
        """
        Calculate price movement percentage based on position direction

        For SHORT: Positive % = price went UP (against position)
        For LONG: Positive % = price went DOWN (against position)
        """
        if direction == 'SHORT':
            # SHORT position loses when price goes UP
            return ((current_price - entry_price) / entry_price) * 100
        else:  # LONG
            # LONG position loses when price goes DOWN
            return ((entry_price - current_price) / entry_price) * 100

    def _calculate_next_margin(self, sequence) -> float:
        """
        Calculate margin for next martingale step

        Based on historical data:
        - First martingale (step 1→2): 2-3x previous margin
        - Subsequent steps: 1.2-1.5x previous margin
        """
        # Get the last signal's margin
        if sequence.signals:
            last_signal = sorted(sequence.signals, key=lambda s: s.step_number)[-1]
            last_margin = last_signal.actual_margin or last_signal.recommended_margin
        else:
            # Fallback to total_margin / current_step
            last_margin = sequence.total_margin / sequence.current_step

        # Calculate multiplier based on current step
        if sequence.current_step == 1:
            # First martingale: use step1_multiplier (2.5x)
            multiplier = self.step1_multiplier
        else:
            # Subsequent martingales: use step2_plus_multiplier (1.35x)
            multiplier = self.step2_plus_multiplier

        next_margin = last_margin * multiplier

        logger.debug(
            f"Next margin: ${last_margin:.2f} × {multiplier} = ${next_margin:.2f}"
        )

        return round(next_margin, 2)

    def _calculate_new_weighted_avg(
        self,
        sequence,
        new_entry_price: float,
        new_margin: float
    ) -> float:
        """
        Calculate new weighted average entry price

        CRITICAL FORMULA:
        weighted_avg = sum(margin_i × entry_i) / sum(margin_i)

        Example:
        - Entry 1: $1.00, margin $20
        - Entry 2: $1.15, margin $50
        - weighted_avg = (1.00×20 + 1.15×50) / (20+50) = 1.093
        """
        current_total_value = sequence.weighted_avg_entry * sequence.total_margin
        new_total_value = current_total_value + (new_entry_price * new_margin)
        new_total_margin = sequence.total_margin + new_margin

        weighted_avg = new_total_value / new_total_margin

        logger.debug(
            f"Weighted avg: (${sequence.weighted_avg_entry:.6f} × ${sequence.total_margin:.2f} + "
            f"${new_entry_price:.6f} × ${new_margin:.2f}) / ${new_total_margin:.2f} = "
            f"${weighted_avg:.6f}"
        )

        return weighted_avg

    def _calculate_new_tps(
        self,
        avg_entry: float,
        direction: str
    ) -> Tuple[float, float]:
        """
        Calculate TP1 and TP2 from weighted average entry

        CRITICAL: Must calculate from weighted avg, NOT first entry!

        For SHORT:
        - TP1 = avg × (1 - tp1_percent/100) = avg × 0.90  (price drops 10%)
        - TP2 = avg × (1 - tp2_percent/100) = avg × 0.85  (price drops 15%)

        For LONG:
        - TP1 = avg × (1 + tp1_percent/100) = avg × 1.10  (price rises 10%)
        - TP2 = avg × (1 + tp2_percent/100) = avg × 1.15  (price rises 15%)
        """
        if direction == 'SHORT':
            tp1 = avg_entry * (1 - self.tp1_percent / 100)
            tp2 = avg_entry * (1 - self.tp2_percent / 100)
        else:  # LONG
            tp1 = avg_entry * (1 + self.tp1_percent / 100)
            tp2 = avg_entry * (1 + self.tp2_percent / 100)

        logger.debug(
            f"New TPs for {direction} from avg ${avg_entry:.6f}: "
            f"TP1=${tp1:.6f}, TP2=${tp2:.6f}"
        )

        return tp1, tp2

    def calculate_sequence_pnl(
        self,
        sequence,
        exit_price: float
    ) -> Dict:
        """
        Calculate PnL for entire sequence

        PnL is calculated from weighted average entry, not first entry!

        Returns:
            Dict with:
            - pnl_pct: Percentage gain/loss from weighted avg
            - total_pnl: Total profit/loss in USDT
            - pnl_per_step: Average PnL per step
        """
        # Calculate PnL percentage from weighted average
        if sequence.direction.value == 'SHORT':
            # SHORT profits when price drops
            pnl_pct = ((sequence.weighted_avg_entry - exit_price) / sequence.weighted_avg_entry) * 100
        else:  # LONG
            # LONG profits when price rises
            pnl_pct = ((exit_price - sequence.weighted_avg_entry) / sequence.weighted_avg_entry) * 100

        # Calculate total PnL in USDT
        # PnL = margin × leverage × (pnl_pct / 100)
        # Assuming average leverage from signals
        avg_leverage = sequence.total_leverage or 20  # Default to 20x
        total_pnl = sequence.total_margin * avg_leverage * (pnl_pct / 100)

        # Calculate average PnL per step
        pnl_per_step = total_pnl / sequence.current_step

        result = {
            'weighted_avg_entry': sequence.weighted_avg_entry,
            'exit_price': exit_price,
            'pnl_pct': pnl_pct,
            'total_pnl': total_pnl,
            'pnl_per_step': pnl_per_step,
            'total_margin': sequence.total_margin,
            'leverage': avg_leverage,
            'steps': sequence.current_step,
        }

        logger.info(
            f"Sequence {sequence.id} PnL: {pnl_pct:+.2f}% = ${total_pnl:+.2f} "
            f"(weighted avg: ${sequence.weighted_avg_entry:.6f}, exit: ${exit_price:.6f})"
        )

        return result

    def check_sequence_close(
        self,
        sequence,
        current_price: float
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if sequence should be closed (TP or SL hit)

        Returns:
            (should_close, outcome) where outcome is one of:
            - 'HIT_TP1', 'HIT_TP2', 'HIT_SL', or None
        """
        if sequence.status.value != 'ACTIVE':
            return False, None

        direction = sequence.direction.value

        if direction == 'SHORT':
            # SHORT: profit when price drops
            if sequence.current_tp2 and current_price <= sequence.current_tp2:
                return True, 'HIT_TP2'
            elif sequence.current_tp1 and current_price <= sequence.current_tp1:
                return True, 'HIT_TP1'
            elif sequence.current_sl and current_price >= sequence.current_sl:
                return True, 'HIT_SL'
        else:  # LONG
            # LONG: profit when price rises
            if sequence.current_tp2 and current_price >= sequence.current_tp2:
                return True, 'HIT_TP2'
            elif sequence.current_tp1 and current_price >= sequence.current_tp1:
                return True, 'HIT_TP1'
            elif sequence.current_sl and current_price <= sequence.current_sl:
                return True, 'HIT_SL'

        return False, None
