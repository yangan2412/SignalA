#!/usr/bin/env python3
"""
Unit tests for MartingaleManager

CRITICAL: Weighted average calculation must be exact!
These tests verify the core formulas match historical trading patterns.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import unittest
from unittest.mock import Mock
from src.strategies.martingale_manager import MartingaleManager
from src.database.models import PositionSequence, BotSignal, TradeDirection, SequenceStatus, SignalType
from datetime import datetime


class TestMartingaleManager(unittest.TestCase):
    """Test MartingaleManager calculations"""

    def setUp(self):
        """Set up test fixtures"""
        self.manager = MartingaleManager(
            max_steps=5,
            trigger_percent=15.0,
            step1_multiplier=2.5,
            step2_plus_multiplier=1.35,
            tp1_percent=10.0,
            tp2_percent=15.0
        )

    def test_weighted_average_two_entries(self):
        """Test weighted average with 2 entries - exact match required"""
        # Scenario:
        # Entry 1: $1.00, margin $20
        # Entry 2: $1.15, margin $50
        # Expected: (1.00×20 + 1.15×50) / (20+50) = (20 + 57.5) / 70 = 1.107142857...

        sequence = Mock()
        sequence.weighted_avg_entry = 1.00
        sequence.total_margin = 20.0

        new_entry = 1.15
        new_margin = 50.0

        result = self.manager._calculate_new_weighted_avg(sequence, new_entry, new_margin)

        expected = (1.00 * 20 + 1.15 * 50) / (20 + 50)
        self.assertAlmostEqual(result, expected, places=6)
        self.assertAlmostEqual(result, 1.107142857142857, places=6)

    def test_weighted_average_three_entries(self):
        """Test weighted average with 3 entries"""
        # Entry 1: $0.006495, margin $20
        # Entry 2: $0.007468, margin $50 (from step 1: 20 × 2.5)
        # Entry 3: $0.008588, margin $67.50 (from step 2: 50 × 1.35)

        # After entry 1:
        sequence = Mock()
        sequence.weighted_avg_entry = 0.006495
        sequence.total_margin = 20.0

        # Add entry 2
        avg_after_2 = self.manager._calculate_new_weighted_avg(
            sequence, 0.007468, 50.0
        )
        expected_after_2 = (0.006495 * 20 + 0.007468 * 50) / (20 + 50)
        self.assertAlmostEqual(avg_after_2, expected_after_2, places=8)

        # Update sequence for entry 3
        sequence.weighted_avg_entry = avg_after_2
        sequence.total_margin = 70.0

        # Add entry 3
        avg_after_3 = self.manager._calculate_new_weighted_avg(
            sequence, 0.008588, 67.50
        )
        expected_after_3 = (avg_after_2 * 70 + 0.008588 * 67.50) / (70 + 67.50)
        self.assertAlmostEqual(avg_after_3, expected_after_3, places=8)

    def test_margin_progression_step1(self):
        """Test margin calculation for first martingale (step 1→2)"""
        sequence = Mock()
        sequence.current_step = 1
        sequence.total_margin = 20.0
        sequence.signals = [Mock(actual_margin=20.0, recommended_margin=20.0, step_number=1)]

        next_margin = self.manager._calculate_next_margin(sequence)

        # First martingale should be 2.5x
        expected = 20.0 * 2.5
        self.assertEqual(next_margin, expected)

    def test_margin_progression_step2_plus(self):
        """Test margin calculation for subsequent martingales (step 2+)"""
        sequence = Mock()
        sequence.current_step = 2
        sequence.total_margin = 70.0
        sequence.signals = [
            Mock(actual_margin=20.0, recommended_margin=20.0, step_number=1),
            Mock(actual_margin=50.0, recommended_margin=50.0, step_number=2)
        ]

        next_margin = self.manager._calculate_next_margin(sequence)

        # Subsequent martingales should be 1.35x
        expected = 50.0 * 1.35
        self.assertEqual(next_margin, expected)

    def test_tp_calculation_short(self):
        """Test TP calculation for SHORT from weighted average"""
        avg_entry = 0.007250
        direction = 'SHORT'

        tp1, tp2 = self.manager._calculate_new_tps(avg_entry, direction)

        # SHORT: TP below entry
        # TP1 = avg × 0.90 (-10%)
        # TP2 = avg × 0.85 (-15%)
        expected_tp1 = avg_entry * 0.90
        expected_tp2 = avg_entry * 0.85

        self.assertAlmostEqual(tp1, expected_tp1, places=8)
        self.assertAlmostEqual(tp2, expected_tp2, places=8)
        self.assertLess(tp2, tp1)  # TP2 should be lower than TP1
        self.assertLess(tp1, avg_entry)  # Both should be below entry

    def test_tp_calculation_long(self):
        """Test TP calculation for LONG from weighted average"""
        avg_entry = 50000.0
        direction = 'LONG'

        tp1, tp2 = self.manager._calculate_new_tps(avg_entry, direction)

        # LONG: TP above entry
        # TP1 = avg × 1.10 (+10%)
        # TP2 = avg × 1.15 (+15%)
        expected_tp1 = avg_entry * 1.10
        expected_tp2 = avg_entry * 1.15

        self.assertAlmostEqual(tp1, expected_tp1, places=2)
        self.assertAlmostEqual(tp2, expected_tp2, places=2)
        self.assertGreater(tp2, tp1)  # TP2 should be higher than TP1
        self.assertGreater(tp1, avg_entry)  # Both should be above entry

    def test_price_move_calculation_short(self):
        """Test price movement calculation for SHORT"""
        entry = 0.006495
        current = 0.007468
        direction = 'SHORT'

        move_pct = self.manager._calculate_price_move_pct(entry, current, direction)

        # SHORT loses when price goes UP
        expected = ((current - entry) / entry) * 100
        self.assertAlmostEqual(move_pct, expected, places=2)
        self.assertGreater(move_pct, 0)  # Should be positive (against position)

    def test_price_move_calculation_long(self):
        """Test price movement calculation for LONG"""
        entry = 50000.0
        current = 45000.0
        direction = 'LONG'

        move_pct = self.manager._calculate_price_move_pct(entry, current, direction)

        # LONG loses when price goes DOWN
        expected = ((entry - current) / entry) * 100
        self.assertAlmostEqual(move_pct, expected, places=2)
        self.assertGreater(move_pct, 0)  # Should be positive (against position)

    def test_should_add_martingale_trigger_met(self):
        """Test martingale trigger when price moved +15%"""
        # Create signal mock
        signal_mock = Mock()
        signal_mock.actual_margin = 20.0
        signal_mock.recommended_margin = 20.0
        signal_mock.step_number = 1

        sequence = Mock()
        sequence.id = 1
        sequence.status = Mock(value='ACTIVE')
        sequence.current_step = 1
        sequence.max_steps = 5
        sequence.first_entry_price = 0.006495
        sequence.last_entry_price = None
        sequence.weighted_avg_entry = 0.006495
        sequence.total_margin = 20.0
        sequence.current_tp1 = 0.005846
        sequence.current_tp2 = 0.005521
        sequence.direction = Mock(value='SHORT')
        sequence.symbol = 'TURBO-USDT'
        sequence.last_martingale_suggestion_at = None
        sequence.signals = [signal_mock]

        # Price moved up 15.5% (to ensure trigger)
        current_price = 0.006495 * 1.155

        should_add, suggestion = self.manager.should_add_martingale(sequence, current_price)

        self.assertTrue(should_add)
        self.assertEqual(suggestion['next_step'], 2)
        self.assertGreaterEqual(suggestion['price_move_pct'], 15.0)

    def test_should_add_martingale_trigger_not_met(self):
        """Test martingale when trigger not met (< 15%)"""
        sequence = Mock()
        sequence.status = Mock(value='ACTIVE')
        sequence.current_step = 1
        sequence.max_steps = 5
        sequence.first_entry_price = 0.006495
        sequence.last_entry_price = None
        sequence.direction = Mock(value='SHORT')
        sequence.last_martingale_suggestion_at = None

        # Price moved up only 10%
        current_price = 0.006495 * 1.10

        should_add, suggestion = self.manager.should_add_martingale(sequence, current_price)

        self.assertFalse(should_add)
        self.assertEqual(suggestion, {})

    def test_should_add_martingale_max_steps_reached(self):
        """Test martingale when max steps reached"""
        sequence = Mock()
        sequence.status = Mock(value='ACTIVE')
        sequence.current_step = 5
        sequence.max_steps = 5
        sequence.first_entry_price = 0.006495
        sequence.last_entry_price = None
        sequence.direction = Mock(value='SHORT')

        # Price moved up 20%
        current_price = 0.006495 * 1.20

        should_add, suggestion = self.manager.should_add_martingale(sequence, current_price)

        self.assertFalse(should_add)
        self.assertEqual(suggestion, {})

    def test_sequence_pnl_calculation_short_profit(self):
        """Test PnL calculation for profitable SHORT sequence"""
        sequence = Mock()
        sequence.id = 1
        sequence.direction = Mock(value='SHORT')
        sequence.weighted_avg_entry = 0.007250  # Averaged from multiple entries
        sequence.total_margin = 70.0
        sequence.total_leverage = 20
        sequence.current_step = 2

        # Exit at TP2 (15% below weighted avg)
        exit_price = 0.007250 * 0.85

        pnl = self.manager.calculate_sequence_pnl(sequence, exit_price)

        # SHORT profit: (avg - exit) / avg × 100 = 15%
        self.assertAlmostEqual(pnl['pnl_pct'], 15.0, places=2)

        # Total PnL: $70 × 20x × 15% = $210
        expected_total = 70.0 * 20 * 0.15
        self.assertAlmostEqual(pnl['total_pnl'], expected_total, places=2)

    def test_sequence_pnl_calculation_short_loss(self):
        """Test PnL calculation for losing SHORT sequence"""
        sequence = Mock()
        sequence.direction = Mock(value='SHORT')
        sequence.weighted_avg_entry = 0.007250
        sequence.total_margin = 70.0
        sequence.total_leverage = 20
        sequence.current_step = 2

        # Exit at SL (5% above weighted avg)
        exit_price = 0.007250 * 1.05

        pnl = self.manager.calculate_sequence_pnl(sequence, exit_price)

        # SHORT loss: (avg - exit) / avg × 100 = -5%
        self.assertAlmostEqual(pnl['pnl_pct'], -5.0, places=2)

        # Total PnL: $70 × 20x × -5% = -$70
        expected_total = 70.0 * 20 * -0.05
        self.assertAlmostEqual(pnl['total_pnl'], expected_total, places=2)

    def test_check_sequence_close_tp2_hit(self):
        """Test sequence close detection when TP2 is hit"""
        sequence = Mock()
        sequence.status = Mock(value='ACTIVE')
        sequence.direction = Mock(value='SHORT')
        sequence.current_tp1 = 0.006525
        sequence.current_tp2 = 0.006163
        sequence.current_sl = None

        # Price drops to TP2
        current_price = 0.006100

        should_close, outcome = self.manager.check_sequence_close(sequence, current_price)

        self.assertTrue(should_close)
        self.assertEqual(outcome, 'HIT_TP2')

    def test_check_sequence_close_tp1_hit(self):
        """Test sequence close detection when TP1 is hit"""
        sequence = Mock()
        sequence.status = Mock(value='ACTIVE')
        sequence.direction = Mock(value='SHORT')
        sequence.current_tp1 = 0.006525
        sequence.current_tp2 = 0.006163
        sequence.current_sl = None

        # Price drops to TP1 (but not TP2)
        current_price = 0.006500

        should_close, outcome = self.manager.check_sequence_close(sequence, current_price)

        self.assertTrue(should_close)
        self.assertEqual(outcome, 'HIT_TP1')

    def test_historical_scenario_turbo(self):
        """
        Test real scenario from Order_His.csv: TURBO-USDT 3-step martingale

        Historical data:
        - Entry 1: $0.006495, margin $20
        - Entry 2: $0.007468, margin $50 (price +15% trigger)
        - Entry 3: $0.008588, margin $67.5 (price +15% trigger)
        - Exit: $0.005651 (TP2 hit)
        - Result: Profit
        """
        # Step 1: Initial entry
        sequence = Mock()
        sequence.weighted_avg_entry = 0.006495
        sequence.total_margin = 20.0
        sequence.current_step = 1
        sequence.max_steps = 5
        sequence.direction = Mock(value='SHORT')
        sequence.signals = [Mock(actual_margin=20.0, recommended_margin=20.0, step_number=1)]

        # Step 2: Add martingale at +15%
        entry_2 = 0.007468
        margin_2 = self.manager._calculate_next_margin(sequence)  # Should be 50
        self.assertAlmostEqual(margin_2, 50.0, places=2)

        avg_after_2 = self.manager._calculate_new_weighted_avg(sequence, entry_2, margin_2)

        # Step 3: Update and add another
        sequence.weighted_avg_entry = avg_after_2
        sequence.total_margin = 70.0
        sequence.current_step = 2
        sequence.signals.append(Mock(actual_margin=50.0, recommended_margin=50.0, step_number=2))

        entry_3 = 0.008588
        margin_3 = self.manager._calculate_next_margin(sequence)  # Should be 67.5
        self.assertAlmostEqual(margin_3, 67.5, places=2)

        avg_after_3 = self.manager._calculate_new_weighted_avg(sequence, entry_3, margin_3)

        # Final: Calculate TP from weighted avg
        sequence.weighted_avg_entry = avg_after_3
        sequence.total_margin = 137.5
        sequence.current_step = 3
        sequence.total_leverage = 25

        tp1, tp2 = self.manager._calculate_new_tps(avg_after_3, 'SHORT')

        # Exit at actual historical price
        exit_price = 0.005651

        # Verify TP2 was hit
        self.assertLess(exit_price, tp2, "Exit price should be below TP2")

        # Calculate profit
        pnl = self.manager.calculate_sequence_pnl(sequence, exit_price)

        # Should be profitable
        self.assertGreater(pnl['total_pnl'], 0, "Historical trade was profitable")
        self.assertGreater(pnl['pnl_pct'], 0, "PnL % should be positive")


def run_tests():
    """Run all tests"""
    print("=" * 60)
    print("🧪 Running MartingaleManager Unit Tests")
    print("=" * 60)
    print()

    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestMartingaleManager)

    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print()
    print("=" * 60)
    if result.wasSuccessful():
        print("✅ ALL TESTS PASSED!")
        print(f"   {result.testsRun} tests run, 0 failures")
        return 0
    else:
        print("❌ SOME TESTS FAILED!")
        print(f"   {result.testsRun} tests run")
        print(f"   {len(result.failures)} failures")
        print(f"   {len(result.errors)} errors")
        return 1


if __name__ == '__main__':
    exit(run_tests())
