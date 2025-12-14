"""
Database manager - CRUD operations và business logic
"""

from sqlalchemy.orm import Session
from .models import (
    Base, UserTrade, BotSignal, SignalResult, SignalPriceUpdate,
    Strategy, PerformanceMetric, PositionSequence,
    TradeDirection, SequenceStatus, SignalType,
    init_db, get_session
)
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import pandas as pd


class DatabaseManager:
    """Quản lý database operations"""

    def __init__(self, database_url='sqlite:///signala.db'):
        self.engine = init_db(database_url)
        self.Session = lambda: get_session(self.engine)

    # ==================== USER TRADES ====================

    def import_user_trades_from_csv(self, csv_file_path: str):
        """Import user trades from CSV or Excel file"""
        # Try to read as Excel first, then fall back to CSV
        try:
            df = pd.read_excel(csv_file_path)
        except:
            df = pd.read_csv(csv_file_path)

        session = self.Session()
        try:
            imported = 0
            skipped = 0

            for _, row in df.iterrows():
                # Handle both BingX API format and Order_His.csv format
                if 'Order No' in df.columns:
                    # Order_His.csv format
                    order_id = str(row.get('Order No', ''))
                    symbol = str(row.get('category', ''))
                    position_side = 'SHORT' if row.get('direction') == 'short' else 'LONG'
                    entry_price = float(row.get('openPrice', 0))
                    close_price = float(row.get('closePrice', 0))
                    avg_price = entry_price
                    margin = float(row.get('margin', 0))
                    leverage = float(row.get('leverage', 1))
                    profit = float(row.get('Realized PNL', 0))
                    stop_loss = float(row.get('stopLossPrice', 0)) if row.get('stopLossPrice') and row.get('stopLossPrice') != 0 else None
                    take_profit = float(row.get('takeProfitPrice', 0)) if row.get('takeProfitPrice') and row.get('takeProfitPrice') != 0 else None
                    entry_time = pd.to_datetime(row.get('openTime(UTC+8)'))
                    close_time = pd.to_datetime(row.get('closeTime(UTC+8)'))
                    quantity = 0  # Not available in Order_His.csv
                    position_value = margin * leverage
                else:
                    # BingX API format
                    order_id = str(row.get('orderId', row.get('order_id', '')))
                    symbol = row.get('symbol', '')
                    position_side = row.get('positionSide', row.get('side', ''))
                    entry_price = float(row.get('avgPrice', row.get('entry_price', 0)))
                    close_price = float(row.get('closePrice', row.get('close_price', 0)))
                    avg_price = float(row.get('avgPrice', row.get('avg_price', 0)))
                    quantity = float(row.get('executedQty', row.get('quantity', 0)))
                    margin = float(row.get('margin', 0))
                    leverage = float(row.get('leverage', 1))
                    position_value = float(row.get('cumQuote', row.get('position_value', 0)))
                    profit = float(row.get('profit', 0)) if 'profit' in row else None
                    stop_loss = float(row.get('stopLoss', 0)) if row.get('stopLoss') else None
                    take_profit = float(row.get('takeProfit', 0)) if row.get('takeProfit') else None
                    entry_time = pd.to_datetime(row.get('time', row.get('entry_time')), unit='ms' if 'time' in row else None)
                    close_time = pd.to_datetime(row.get('updateTime', row.get('close_time')), unit='ms' if 'updateTime' in row else None)

                # Check if already exists
                existing = session.query(UserTrade).filter_by(
                    order_id=order_id
                ).first()

                if existing:
                    skipped += 1
                    continue

                # Create trade
                trade = UserTrade(
                    order_id=order_id,
                    symbol=symbol,
                    position_side=position_side,
                    entry_price=entry_price,
                    close_price=close_price,
                    avg_price=avg_price,
                    quantity=quantity,
                    margin=margin,
                    leverage=leverage,
                    position_value=position_value,
                    profit=profit,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    entry_time=entry_time,
                    close_time=close_time,
                    status='CLOSED'
                )

                session.add(trade)
                imported += 1

            session.commit()
            return {'imported': imported, 'skipped': skipped, 'total': len(df)}

        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def get_user_trades(self,
                       symbol: Optional[str] = None,
                       position_side: Optional[str] = None,
                       start_date: Optional[datetime] = None,
                       end_date: Optional[datetime] = None,
                       limit: Optional[int] = None) -> List[UserTrade]:
        """Get user trades with filters"""
        session = self.Session()
        try:
            query = session.query(UserTrade)

            if symbol:
                query = query.filter(UserTrade.symbol == symbol)
            if position_side:
                query = query.filter(UserTrade.position_side == position_side)
            if start_date:
                query = query.filter(UserTrade.entry_time >= start_date)
            if end_date:
                query = query.filter(UserTrade.entry_time <= end_date)

            query = query.order_by(UserTrade.entry_time.desc())

            if limit:
                query = query.limit(limit)

            return query.all()
        finally:
            session.close()

    # ==================== BOT SIGNALS ====================

    def create_signal(self, signal_data: Dict, sequence_id: Optional[int] = None) -> BotSignal:
        """Tạo signal mới khi bot gửi"""
        session = self.Session()
        try:
            signal = BotSignal(
                symbol=signal_data['symbol'],
                direction=signal_data['side'],
                entry_price=signal_data['entry_price'],
                stop_loss=signal_data['stop_loss'],
                take_profit_1=signal_data['take_profit_1'],
                take_profit_2=signal_data['take_profit_2'],
                confidence=signal_data.get('confidence', 0.5),
                strategy_name=signal_data.get('strategy', 'Unknown'),
                rsi=signal_data.get('indicators', {}).get('rsi'),
                macd=signal_data.get('indicators', {}).get('macd'),
                recommended_leverage=signal_data.get('recommended_leverage', 20),
                recommended_margin=signal_data.get('recommended_margin', 10),
                status='ACTIVE',
                telegram_message_id=signal_data.get('telegram_message_id'),
                chat_id=signal_data.get('chat_id'),
                # Martingale fields
                signal_type=SignalType[signal_data.get('signal_type', 'STANDALONE')],
                sequence_id=sequence_id,
                step_number=signal_data.get('step_number', 1),
                actual_margin=signal_data.get('actual_margin', signal_data.get('recommended_margin', 10))
            )

            session.add(signal)
            session.commit()
            session.refresh(signal)

            return signal
        finally:
            session.close()

    def update_signal_price(self, signal_id: int, current_price: float):
        """Cập nhật giá hiện tại cho signal"""
        session = self.Session()
        try:
            signal = session.query(BotSignal).filter_by(id=signal_id).first()
            if not signal:
                return None

            # Calculate distances
            price_change_pct = ((current_price - signal.entry_price) / signal.entry_price) * 100

            if signal.direction == 'SHORT':
                price_change_pct = -price_change_pct

            distance_to_sl = abs(((signal.stop_loss - current_price) / current_price) * 100)
            distance_to_tp1 = abs(((signal.take_profit_1 - current_price) / current_price) * 100)
            distance_to_tp2 = abs(((signal.take_profit_2 - current_price) / current_price) * 100)

            # Create price update
            update = SignalPriceUpdate(
                signal_id=signal_id,
                current_price=current_price,
                price_change_pct=price_change_pct,
                distance_to_sl_pct=distance_to_sl,
                distance_to_tp1_pct=distance_to_tp1,
                distance_to_tp2_pct=distance_to_tp2
            )

            session.add(update)

            # Check if hit TP/SL
            outcome = self._check_signal_outcome(signal, current_price)
            if outcome:
                self._close_signal(session, signal, current_price, outcome)

            session.commit()
            return update

        finally:
            session.close()

    def _check_signal_outcome(self, signal: BotSignal, current_price: float) -> Optional[str]:
        """Check if signal hit TP or SL"""
        if signal.direction == 'LONG':
            # LONG: giá tăng lên TP, giảm xuống SL
            if current_price >= signal.take_profit_2:
                return 'HIT_TP2'
            elif current_price >= signal.take_profit_1:
                return 'HIT_TP1'
            elif current_price <= signal.stop_loss:
                return 'HIT_SL'
        else:  # SHORT
            # SHORT: giá giảm xuống TP, tăng lên SL
            if current_price <= signal.take_profit_2:
                return 'HIT_TP2'
            elif current_price <= signal.take_profit_1:
                return 'HIT_TP1'
            elif current_price >= signal.stop_loss:
                return 'HIT_SL'

        # Check expiration (48 hours)
        if (datetime.utcnow() - signal.signal_time).total_seconds() > 48 * 3600:
            return 'EXPIRED'

        return None

    def _close_signal(self, session: Session, signal: BotSignal, exit_price: float, outcome: str):
        """Close signal và tạo result"""
        # Update signal status
        signal.status = 'CLOSED'

        # Calculate PnL (theoretical)
        if signal.direction == 'LONG':
            pnl_pct = ((exit_price - signal.entry_price) / signal.entry_price) * 100
        else:  # SHORT
            pnl_pct = ((signal.entry_price - exit_price) / signal.entry_price) * 100

        # Theoretical PnL with recommended margin
        margin = signal.recommended_margin or 10
        leverage = signal.recommended_leverage or 20
        theoretical_pnl = margin * leverage * (pnl_pct / 100)

        is_win = outcome in ['HIT_TP1', 'HIT_TP2']

        # Get price range
        price_updates = session.query(SignalPriceUpdate).filter_by(signal_id=signal.id).all()
        prices = [u.current_price for u in price_updates]
        max_price = max(prices) if prices else exit_price
        min_price = min(prices) if prices else exit_price

        # Create result
        result = SignalResult(
            signal_id=signal.id,
            outcome=outcome,
            actual_entry_price=signal.entry_price,
            actual_exit_price=exit_price,
            theoretical_pnl=theoretical_pnl,
            theoretical_pnl_pct=pnl_pct,
            entry_time=signal.signal_time,
            exit_time=datetime.utcnow(),
            duration_hours=(datetime.utcnow() - signal.signal_time).total_seconds() / 3600,
            max_price_reached=max_price,
            min_price_reached=min_price,
            is_win=is_win
        )

        session.add(result)

    def get_active_signals(self) -> List[BotSignal]:
        """Get all active signals để track"""
        session = self.Session()
        try:
            return session.query(BotSignal).filter_by(status='ACTIVE').all()
        finally:
            session.close()

    def get_signal_by_id(self, signal_id: int) -> Optional[BotSignal]:
        """Get signal by ID"""
        session = self.Session()
        try:
            return session.query(BotSignal).filter_by(id=signal_id).first()
        finally:
            session.close()

    # ==================== POSITION SEQUENCES (MARTINGALE) ====================

    def create_sequence(self, signal_data: Dict) -> PositionSequence:
        """
        Create new position sequence from INITIAL signal

        Args:
            signal_data: Signal data containing entry price, margin, TPs, etc.

        Returns:
            PositionSequence object
        """
        session = self.Session()
        try:
            # Convert direction string to enum
            direction = TradeDirection.SHORT if signal_data['side'] == 'SHORT' else TradeDirection.LONG

            # Get initial parameters
            entry_price = signal_data['entry_price']
            margin = signal_data.get('recommended_margin', 20)
            leverage = signal_data.get('recommended_leverage', 20)

            # Initially, weighted avg = first entry
            sequence = PositionSequence(
                symbol=signal_data['symbol'],
                direction=direction,
                status=SequenceStatus.ACTIVE,
                current_step=1,
                max_steps=signal_data.get('max_steps', 5),
                first_entry_price=entry_price,
                last_entry_price=entry_price,
                weighted_avg_entry=entry_price,  # Initially same as first entry
                total_margin=margin,
                total_leverage=leverage,
                current_tp1=signal_data.get('take_profit_1'),
                current_tp2=signal_data.get('take_profit_2'),
                current_sl=signal_data.get('stop_loss'),
                trigger_percent=signal_data.get('trigger_percent', 15.0),
                step1_multiplier=signal_data.get('step1_multiplier', 2.5),
                step2_plus_multiplier=signal_data.get('step2_plus_multiplier', 1.35),
                strategy_name=signal_data.get('strategy', 'Unknown'),
                confidence=signal_data.get('confidence', 0.5)
            )

            session.add(sequence)
            session.commit()
            session.refresh(sequence)

            return sequence
        finally:
            session.close()

    def add_martingale_to_sequence(
        self,
        sequence_id: int,
        entry_price: float,
        margin: float,
        leverage: Optional[float] = None
    ) -> PositionSequence:
        """
        Add martingale entry to sequence and recalculate weighted avg + TPs

        Args:
            sequence_id: ID of the position sequence
            entry_price: New entry price
            margin: New margin amount
            leverage: Optional leverage (uses sequence's leverage if not provided)

        Returns:
            Updated PositionSequence object
        """
        session = self.Session()
        try:
            sequence = session.query(PositionSequence).filter_by(id=sequence_id).first()
            if not sequence:
                raise ValueError(f"Sequence {sequence_id} not found")

            if sequence.status != SequenceStatus.ACTIVE:
                raise ValueError(f"Sequence {sequence_id} is not active")

            # Recalculate weighted average
            current_total_value = sequence.weighted_avg_entry * sequence.total_margin
            new_total_value = current_total_value + (entry_price * margin)
            new_total_margin = sequence.total_margin + margin
            new_weighted_avg = new_total_value / new_total_margin

            # Recalculate TPs from new weighted avg
            if sequence.direction == TradeDirection.SHORT:
                # SHORT: TP below entry
                new_tp1 = new_weighted_avg * 0.90  # -10%
                new_tp2 = new_weighted_avg * 0.85  # -15%
            else:  # LONG
                # LONG: TP above entry
                new_tp1 = new_weighted_avg * 1.10  # +10%
                new_tp2 = new_weighted_avg * 1.15  # +15%

            # Update sequence
            sequence.current_step += 1
            sequence.last_entry_price = entry_price
            sequence.weighted_avg_entry = new_weighted_avg
            sequence.total_margin = new_total_margin
            sequence.current_tp1 = new_tp1
            sequence.current_tp2 = new_tp2

            if leverage:
                sequence.total_leverage = leverage

            sequence.updated_at = datetime.utcnow()

            session.commit()
            session.refresh(sequence)

            return sequence
        finally:
            session.close()

    def get_active_sequences(self) -> List[PositionSequence]:
        """Get all active position sequences with eagerly loaded signals"""
        from sqlalchemy.orm import joinedload
        session = self.Session()
        try:
            sequences = session.query(PositionSequence).options(
                joinedload(PositionSequence.signals)
            ).filter_by(
                status=SequenceStatus.ACTIVE
            ).all()
            # Expunge all sequences from session to make them usable after session closes
            for seq in sequences:
                _ = seq.signals  # Access to load
                session.expunge(seq)
            return sequences
        finally:
            session.close()

    def get_sequence_by_id(self, sequence_id: int) -> Optional[PositionSequence]:
        """Get sequence by ID with eagerly loaded signals"""
        from sqlalchemy.orm import joinedload
        session = self.Session()
        try:
            sequence = session.query(PositionSequence).options(
                joinedload(PositionSequence.signals)
            ).filter_by(id=sequence_id).first()
            if sequence:
                # Access signals to load them before session closes
                _ = sequence.signals
                session.expunge(sequence)
            return sequence
        finally:
            session.close()

    def close_sequence(
        self,
        sequence_id: int,
        exit_price: float,
        outcome: str
    ) -> PositionSequence:
        """
        Close position sequence and calculate final PnL

        Args:
            sequence_id: ID of the sequence
            exit_price: Final exit price
            outcome: Outcome string (HIT_TP1, HIT_TP2, HIT_SL, etc.)

        Returns:
            Closed PositionSequence object
        """
        session = self.Session()
        try:
            sequence = session.query(PositionSequence).filter_by(id=sequence_id).first()
            if not sequence:
                raise ValueError(f"Sequence {sequence_id} not found")

            # Calculate PnL from weighted average (NOT first entry!)
            if sequence.direction == TradeDirection.SHORT:
                # SHORT profits when price drops
                pnl_pct = ((sequence.weighted_avg_entry - exit_price) / sequence.weighted_avg_entry) * 100
            else:  # LONG
                # LONG profits when price rises
                pnl_pct = ((exit_price - sequence.weighted_avg_entry) / sequence.weighted_avg_entry) * 100

            # Total PnL in USDT
            leverage = sequence.total_leverage or 20
            total_pnl = sequence.total_margin * leverage * (pnl_pct / 100)

            # Update sequence
            sequence.status = SequenceStatus[outcome]
            sequence.closed_at = datetime.utcnow()
            sequence.final_exit_price = exit_price
            sequence.total_pnl = total_pnl
            sequence.total_pnl_pct = pnl_pct
            sequence.updated_at = datetime.utcnow()

            # Close all signals in sequence
            for signal in sequence.signals:
                if signal.status == 'ACTIVE':
                    signal.status = 'CLOSED'

                    # Create result for each signal
                    if signal.direction == 'LONG':
                        signal_pnl_pct = ((exit_price - signal.entry_price) / signal.entry_price) * 100
                    else:  # SHORT
                        signal_pnl_pct = ((signal.entry_price - exit_price) / signal.entry_price) * 100

                    signal_margin = signal.actual_margin or signal.recommended_margin
                    signal_leverage = signal.recommended_leverage or 20
                    signal_pnl = signal_margin * signal_leverage * (signal_pnl_pct / 100)

                    result = SignalResult(
                        signal_id=signal.id,
                        outcome=outcome,
                        actual_entry_price=signal.entry_price,
                        actual_exit_price=exit_price,
                        theoretical_pnl=signal_pnl,
                        theoretical_pnl_pct=signal_pnl_pct,
                        entry_time=signal.signal_time,
                        exit_time=datetime.utcnow(),
                        duration_hours=(datetime.utcnow() - signal.signal_time).total_seconds() / 3600,
                        is_win=outcome in ['HIT_TP1', 'HIT_TP2']
                    )
                    session.add(result)

            session.commit()
            session.refresh(sequence)

            return sequence
        finally:
            session.close()

    def update_sequence_martingale_suggestion_time(self, sequence_id: int):
        """Update last martingale suggestion time to prevent spam"""
        session = self.Session()
        try:
            sequence = session.query(PositionSequence).filter_by(id=sequence_id).first()
            if sequence:
                sequence.last_martingale_suggestion_at = datetime.utcnow()
                session.commit()
        finally:
            session.close()

    # ==================== PERFORMANCE ====================

    def get_bot_performance(self, days: int = 30) -> Dict:
        """Get bot performance stats"""
        session = self.Session()
        try:
            start_date = datetime.utcnow() - timedelta(days=days)

            signals = session.query(BotSignal).filter(
                BotSignal.signal_time >= start_date,
                BotSignal.status == 'CLOSED'
            ).all()

            if not signals:
                return {
                    'total_signals': 0,
                    'win_rate': 0,
                    'total_pnl': 0,
                    'avg_pnl': 0
                }

            results = [s.result for s in signals if s.result]

            total_signals = len(results)
            winning_signals = sum(1 for r in results if r.is_win)
            win_rate = (winning_signals / total_signals * 100) if total_signals > 0 else 0

            total_pnl = sum(r.theoretical_pnl for r in results)
            avg_pnl = total_pnl / total_signals if total_signals > 0 else 0

            return {
                'total_signals': total_signals,
                'winning_signals': winning_signals,
                'losing_signals': total_signals - winning_signals,
                'win_rate': round(win_rate, 2),
                'total_pnl': round(total_pnl, 2),
                'avg_pnl': round(avg_pnl, 2),
                'best_signal': max([r.theoretical_pnl for r in results]) if results else 0,
                'worst_signal': min([r.theoretical_pnl for r in results]) if results else 0
            }

        finally:
            session.close()

    def generate_performance_report(self) -> str:
        """Generate text performance report"""
        perf = self.get_bot_performance()

        report = f"""
╔════════════════════════════════════════════════════════════╗
║            BOT PERFORMANCE REPORT (30 Days)               ║
╚════════════════════════════════════════════════════════════╝

📊 SIGNALS SENT:
   • Total: {perf['total_signals']}
   • Won: {perf['winning_signals']}
   • Lost: {perf['losing_signals']}
   • Win Rate: {perf['win_rate']}%

💰 THEORETICAL PnL:
   • Total: ${perf['total_pnl']:+.2f}
   • Average: ${perf['avg_pnl']:+.2f}
   • Best: ${perf['best_signal']:+.2f}
   • Worst: ${perf['worst_signal']:+.2f}

⚠️ Note: This is theoretical PnL based on recommended position size.
         Actual results may vary based on your actual trades.
"""
        return report

    # ==================== COMPARISON ====================

    def compare_bot_vs_user(self, days: int = 30) -> Dict:
        """So sánh performance bot vs user thực tế"""
        session = self.Session()
        try:
            start_date = datetime.utcnow() - timedelta(days=days)

            # Bot performance
            bot_perf = self.get_bot_performance(days)

            # User performance
            user_trades = self.get_user_trades(start_date=start_date)
            user_profitable = [t for t in user_trades if t.profit and t.profit > 0]
            user_total = len(user_trades)

            user_win_rate = (len(user_profitable) / user_total * 100) if user_total > 0 else 0
            user_total_pnl = sum(t.profit for t in user_trades if t.profit) if user_trades else 0

            return {
                'bot': bot_perf,
                'user': {
                    'total_trades': user_total,
                    'win_rate': round(user_win_rate, 2),
                    'total_pnl': round(user_total_pnl, 2)
                }
            }

        finally:
            session.close()
