"""
Database models cho SignalA Trading Bot
"""

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import enum

Base = declarative_base()


class TradeDirection(enum.Enum):
    """Trade direction enum"""
    LONG = "LONG"
    SHORT = "SHORT"


class SignalStatus(enum.Enum):
    """Signal status enum"""
    PENDING = "PENDING"          # Chờ xác nhận
    ACTIVE = "ACTIVE"            # Đang theo dõi
    HIT_TP1 = "HIT_TP1"         # Đạt TP1
    HIT_TP2 = "HIT_TP2"         # Đạt TP2
    HIT_SL = "HIT_SL"           # Đạt Stop Loss
    EXPIRED = "EXPIRED"          # Hết hạn (không đạt TP/SL)
    CANCELLED = "CANCELLED"      # Hủy bỏ


class SignalType(enum.Enum):
    """Signal type for martingale tracking"""
    INITIAL = "INITIAL"          # First entry of a martingale sequence
    MARTINGALE = "MARTINGALE"    # Additional entry in sequence
    STANDALONE = "STANDALONE"    # Single trade (no martingale)


class SequenceStatus(enum.Enum):
    """Position sequence status"""
    ACTIVE = "ACTIVE"                  # Sequence đang mở
    CLOSED_TP1 = "CLOSED_TP1"         # Đóng tại TP1
    CLOSED_TP2 = "CLOSED_TP2"         # Đóng tại TP2
    CLOSED_SL = "CLOSED_SL"           # Đóng tại SL
    CLOSED_MANUAL = "CLOSED_MANUAL"   # Đóng thủ công
    EXPIRED = "EXPIRED"                # Hết hạn timeout
    CANCELLED = "CANCELLED"            # Hủy bỏ


class UserTrade(Base):
    """Lịch sử giao dịch thực tế của user từ BingX"""
    __tablename__ = 'user_trades'

    id = Column(Integer, primary_key=True)

    # Trade info
    order_id = Column(String(100), unique=True, nullable=False)
    symbol = Column(String(50), nullable=False)
    position_side = Column(String(10), nullable=False)  # LONG/SHORT

    # Prices
    entry_price = Column(Float, nullable=False)
    close_price = Column(Float)
    avg_price = Column(Float)

    # Position details
    quantity = Column(Float, nullable=False)
    margin = Column(Float, nullable=False)
    leverage = Column(Float, nullable=False)
    position_value = Column(Float)

    # PnL
    profit = Column(Float)
    profit_pct = Column(Float)

    # Stop Loss / Take Profit
    stop_loss = Column(Float)
    take_profit = Column(Float)

    # Timestamps
    entry_time = Column(DateTime, nullable=False)
    close_time = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Status
    status = Column(String(20))  # OPEN, CLOSED, etc.

    # Metadata
    notes = Column(Text)

    def __repr__(self):
        return f"<UserTrade {self.symbol} {self.position_side} {self.entry_price}>"


class PositionSequence(Base):
    """Martingale position sequence - tracks chain of related entries"""
    __tablename__ = 'position_sequences'

    id = Column(Integer, primary_key=True)

    # Symbol and direction
    symbol = Column(String(50), nullable=False)
    direction = Column(Enum(TradeDirection), nullable=False)  # LONG/SHORT
    status = Column(Enum(SequenceStatus), default=SequenceStatus.ACTIVE)

    # Sequence tracking
    current_step = Column(Integer, default=1)
    max_steps = Column(Integer, default=5)

    # Price tracking
    first_entry_price = Column(Float, nullable=False)
    last_entry_price = Column(Float)
    weighted_avg_entry = Column(Float, nullable=False)  # CRITICAL for TP/SL calculation

    # Position size
    total_margin = Column(Float, nullable=False)
    total_leverage = Column(Float)

    # Current targets (recalculated after each martingale step)
    current_tp1 = Column(Float)
    current_tp2 = Column(Float)
    current_sl = Column(Float, nullable=True)  # May be None for martingale mode

    # Martingale parameters
    trigger_percent = Column(Float, default=15.0)      # Price move % to trigger next step
    step1_multiplier = Column(Float, default=2.5)      # Margin multiplier for first martingale
    step2_plus_multiplier = Column(Float, default=1.35)  # Margin multiplier for step 2+

    # Timestamps
    opened_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    closed_at = Column(DateTime)
    last_martingale_suggestion_at = Column(DateTime)  # Prevent spam suggestions

    # Results (filled when sequence closes)
    final_exit_price = Column(Float)
    total_pnl = Column(Float)
    total_pnl_pct = Column(Float)

    # Strategy info
    strategy_name = Column(String(100))
    confidence = Column(Float)

    # Notes
    notes = Column(Text)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    signals = relationship("BotSignal", back_populates="sequence", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<PositionSequence {self.symbol} {self.direction.value} step={self.current_step}/{self.max_steps}>"


class BotSignal(Base):
    """Tín hiệu mà bot đã gửi đi"""
    __tablename__ = 'bot_signals'

    id = Column(Integer, primary_key=True)

    # Signal info
    symbol = Column(String(50), nullable=False)
    direction = Column(String(10), nullable=False)  # LONG/SHORT

    # Entry
    entry_price = Column(Float, nullable=False)
    recommended_leverage = Column(Float)
    recommended_margin = Column(Float)

    # Exit levels
    stop_loss = Column(Float, nullable=False)
    take_profit_1 = Column(Float, nullable=False)
    take_profit_2 = Column(Float, nullable=False)

    # Signal metadata
    confidence = Column(Float)  # 0-1
    strategy_name = Column(String(100))

    # Indicators at signal time
    rsi = Column(Float)
    macd = Column(Float)
    ema_50 = Column(Float)
    ema_200 = Column(Float)

    # Timestamps
    signal_time = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Status tracking
    status = Column(String(20), default='PENDING')  # PENDING, ACTIVE, CLOSED

    # Telegram info
    telegram_message_id = Column(String(100))
    chat_id = Column(String(100))

    # Martingale sequence tracking
    signal_type = Column(Enum(SignalType), default=SignalType.STANDALONE)
    sequence_id = Column(Integer, ForeignKey('position_sequences.id'), nullable=True)
    step_number = Column(Integer, default=1)
    actual_margin = Column(Float)  # Actual margin used (may differ from recommended)

    # Relationships
    sequence = relationship("PositionSequence", back_populates="signals")
    result = relationship("SignalResult", back_populates="signal", uselist=False)
    price_updates = relationship("SignalPriceUpdate", back_populates="signal")

    def __repr__(self):
        return f"<BotSignal {self.symbol} {self.direction} @ {self.entry_price}>"


class SignalResult(Base):
    """Kết quả của một signal (ăn/lỗ)"""
    __tablename__ = 'signal_results'

    id = Column(Integer, primary_key=True)
    signal_id = Column(Integer, ForeignKey('bot_signals.id'), nullable=False)

    # Result
    outcome = Column(String(20))  # HIT_TP1, HIT_TP2, HIT_SL, EXPIRED

    # Actual prices
    actual_entry_price = Column(Float)
    actual_exit_price = Column(Float)

    # PnL (theoretical - based on recommended position)
    theoretical_pnl = Column(Float)
    theoretical_pnl_pct = Column(Float)

    # Timing
    entry_time = Column(DateTime)
    exit_time = Column(DateTime)
    duration_hours = Column(Float)

    # What happened
    max_price_reached = Column(Float)
    min_price_reached = Column(Float)

    # Win/Loss
    is_win = Column(Boolean)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Notes
    notes = Column(Text)

    # Relationship
    signal = relationship("BotSignal", back_populates="result")

    def __repr__(self):
        return f"<SignalResult signal_id={self.signal_id} outcome={self.outcome}>"


class SignalPriceUpdate(Base):
    """Tracking giá theo thời gian thực cho mỗi signal"""
    __tablename__ = 'signal_price_updates'

    id = Column(Integer, primary_key=True)
    signal_id = Column(Integer, ForeignKey('bot_signals.id'), nullable=False)

    # Price info
    current_price = Column(Float, nullable=False)
    price_change_pct = Column(Float)

    # Distance to targets
    distance_to_sl_pct = Column(Float)
    distance_to_tp1_pct = Column(Float)
    distance_to_tp2_pct = Column(Float)

    # Timestamp
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationship
    signal = relationship("BotSignal", back_populates="price_updates")

    def __repr__(self):
        return f"<SignalPriceUpdate signal_id={self.signal_id} price={self.current_price}>"


class Strategy(Base):
    """Các strategies khác nhau"""
    __tablename__ = 'strategies'

    id = Column(Integer, primary_key=True)

    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text)

    # Parameters (JSON string)
    parameters = Column(Text)

    # Active/Inactive
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Performance metrics
    total_signals = Column(Integer, default=0)
    winning_signals = Column(Integer, default=0)
    losing_signals = Column(Integer, default=0)
    win_rate = Column(Float, default=0.0)
    total_pnl = Column(Float, default=0.0)

    def __repr__(self):
        return f"<Strategy {self.name}>"


class PerformanceMetric(Base):
    """Metrics theo thời gian để track bot performance"""
    __tablename__ = 'performance_metrics'

    id = Column(Integer, primary_key=True)

    # Time period
    date = Column(DateTime, nullable=False)
    period_type = Column(String(20))  # DAILY, WEEKLY, MONTHLY

    # Signal stats
    signals_sent = Column(Integer, default=0)
    signals_won = Column(Integer, default=0)
    signals_lost = Column(Integer, default=0)
    win_rate = Column(Float, default=0.0)

    # PnL stats
    total_pnl = Column(Float, default=0.0)
    avg_pnl_per_signal = Column(Float, default=0.0)
    best_signal_pnl = Column(Float, default=0.0)
    worst_signal_pnl = Column(Float, default=0.0)

    # Risk metrics
    max_drawdown = Column(Float, default=0.0)
    sharpe_ratio = Column(Float)

    # By direction
    long_signals = Column(Integer, default=0)
    short_signals = Column(Integer, default=0)
    long_win_rate = Column(Float, default=0.0)
    short_win_rate = Column(Float, default=0.0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<PerformanceMetric {self.period_type} {self.date}>"


# Database helper functions
def init_db(database_url='sqlite:///signala.db'):
    """Initialize database"""
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    return engine


def get_session(engine):
    """Get database session"""
    Session = sessionmaker(bind=engine)
    return Session()
