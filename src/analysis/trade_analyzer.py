import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)

class TradeAnalyzer:
    """Phân tích lịch sử giao dịch để tìm patterns và insights"""

    def __init__(self, trades: List[Dict]):
        """
        Initialize analyzer with trade data

        Args:
            trades: List of trade records from BingX API
        """
        self.trades = trades
        self.df = self._prepare_dataframe()

    def _prepare_dataframe(self) -> pd.DataFrame:
        """Convert trade list to pandas DataFrame"""
        if not self.trades:
            return pd.DataFrame()

        df = pd.DataFrame(self.trades)

        # Convert timestamps
        if 'time' in df.columns:
            df['time'] = pd.to_datetime(df['time'], unit='ms')
        if 'updateTime' in df.columns:
            df['updateTime'] = pd.to_datetime(df['updateTime'], unit='ms')

        # Convert numeric columns
        numeric_columns = ['price', 'avgPrice', 'origQty', 'executedQty', 'profit', 'stopLoss', 'takeProfit']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        return df

    def get_summary_stats(self) -> Dict:
        """Tính toán thống kê tổng quan"""
        if self.df.empty:
            return {}

        total_trades = len(self.df)
        profitable_trades = len(self.df[self.df['profit'] > 0]) if 'profit' in self.df.columns else 0
        losing_trades = len(self.df[self.df['profit'] < 0]) if 'profit' in self.df.columns else 0

        win_rate = (profitable_trades / total_trades * 100) if total_trades > 0 else 0

        total_profit = self.df['profit'].sum() if 'profit' in self.df.columns else 0
        avg_profit = self.df[self.df['profit'] > 0]['profit'].mean() if profitable_trades > 0 else 0
        avg_loss = abs(self.df[self.df['profit'] < 0]['profit'].mean()) if losing_trades > 0 else 0

        risk_reward_ratio = (avg_profit / avg_loss) if avg_loss > 0 else 0

        # Long vs Short
        long_trades = len(self.df[self.df['side'] == 'BUY']) if 'side' in self.df.columns else 0
        short_trades = len(self.df[self.df['side'] == 'SELL']) if 'side' in self.df.columns else 0

        return {
            'total_trades': total_trades,
            'profitable_trades': profitable_trades,
            'losing_trades': losing_trades,
            'win_rate': round(win_rate, 2),
            'total_profit': round(total_profit, 2),
            'avg_profit': round(avg_profit, 2),
            'avg_loss': round(avg_loss, 2),
            'risk_reward_ratio': round(risk_reward_ratio, 2),
            'long_trades': long_trades,
            'short_trades': short_trades,
            'long_percentage': round(long_trades / total_trades * 100, 2) if total_trades > 0 else 0,
        }

    def get_symbol_performance(self) -> pd.DataFrame:
        """Phân tích performance theo từng symbol"""
        if self.df.empty or 'symbol' not in self.df.columns:
            return pd.DataFrame()

        symbol_stats = self.df.groupby('symbol').agg({
            'profit': ['count', 'sum', 'mean'],
        }).round(2)

        symbol_stats.columns = ['trades', 'total_profit', 'avg_profit']

        # Tính win rate cho mỗi symbol
        win_rates = []
        for symbol in symbol_stats.index:
            symbol_trades = self.df[self.df['symbol'] == symbol]
            wins = len(symbol_trades[symbol_trades['profit'] > 0])
            total = len(symbol_trades)
            win_rate = (wins / total * 100) if total > 0 else 0
            win_rates.append(round(win_rate, 2))

        symbol_stats['win_rate'] = win_rates
        symbol_stats = symbol_stats.sort_values('total_profit', ascending=False)

        return symbol_stats

    def get_time_based_analysis(self) -> Dict:
        """Phân tích theo thời gian (giờ trong ngày, ngày trong tuần)"""
        if self.df.empty or 'time' not in self.df.columns:
            return {}

        # Thêm columns cho phân tích
        self.df['hour'] = self.df['time'].dt.hour
        self.df['day_of_week'] = self.df['time'].dt.day_name()
        self.df['is_win'] = self.df['profit'] > 0

        # Win rate theo giờ
        hourly_stats = self.df.groupby('hour').agg({
            'profit': ['count', 'sum'],
            'is_win': 'mean'
        }).round(2)

        hourly_stats.columns = ['trades', 'total_profit', 'win_rate']
        hourly_stats['win_rate'] = (hourly_stats['win_rate'] * 100).round(2)

        # Win rate theo ngày trong tuần
        daily_stats = self.df.groupby('day_of_week').agg({
            'profit': ['count', 'sum'],
            'is_win': 'mean'
        }).round(2)

        daily_stats.columns = ['trades', 'total_profit', 'win_rate']
        daily_stats['win_rate'] = (daily_stats['win_rate'] * 100).round(2)

        # Tìm khung giờ tốt nhất
        best_hours = hourly_stats.nlargest(3, 'win_rate').index.tolist()
        worst_hours = hourly_stats.nsmallest(3, 'win_rate').index.tolist()

        return {
            'hourly_stats': hourly_stats.to_dict('index'),
            'daily_stats': daily_stats.to_dict('index'),
            'best_trading_hours': best_hours,
            'worst_trading_hours': worst_hours,
        }

    def get_position_size_analysis(self) -> Dict:
        """Phân tích position size"""
        if self.df.empty or 'origQty' not in self.df.columns:
            return {}

        # Chia position size thành các nhóm
        self.df['size_category'] = pd.qcut(
            self.df['origQty'],
            q=3,
            labels=['Small', 'Medium', 'Large'],
            duplicates='drop'
        )

        size_stats = self.df.groupby('size_category').agg({
            'profit': ['count', 'sum', 'mean'],
        }).round(2)

        size_stats.columns = ['trades', 'total_profit', 'avg_profit']

        # Win rate theo size
        win_rates = []
        for category in size_stats.index:
            cat_trades = self.df[self.df['size_category'] == category]
            wins = len(cat_trades[cat_trades['profit'] > 0])
            total = len(cat_trades)
            win_rate = (wins / total * 100) if total > 0 else 0
            win_rates.append(round(win_rate, 2))

        size_stats['win_rate'] = win_rates

        return size_stats.to_dict('index')

    def identify_patterns(self) -> Dict:
        """Tìm các patterns quan trọng"""
        patterns = {
            'consecutive_wins': self._find_consecutive_results(True),
            'consecutive_losses': self._find_consecutive_results(False),
            'revenge_trading': self._detect_revenge_trading(),
            'overtrading_days': self._detect_overtrading(),
        }

        return patterns

    def _find_consecutive_results(self, is_win: bool) -> int:
        """Tìm chuỗi thắng/thua liên tiếp dài nhất"""
        if self.df.empty:
            return 0

        streak = 0
        max_streak = 0

        for profit in self.df['profit']:
            if (profit > 0) == is_win:
                streak += 1
                max_streak = max(max_streak, streak)
            else:
                streak = 0

        return max_streak

    def _detect_revenge_trading(self) -> int:
        """Phát hiện revenge trading (giao dịch liên tục sau khi thua)"""
        if self.df.empty or 'time' not in self.df.columns:
            return 0

        revenge_count = 0
        for i in range(1, len(self.df)):
            # Nếu trade trước thua và trade sau trong vòng 5 phút
            prev_loss = self.df.iloc[i-1]['profit'] < 0
            time_diff = (self.df.iloc[i]['time'] - self.df.iloc[i-1]['time']).total_seconds()

            if prev_loss and time_diff < 300:  # 5 minutes
                revenge_count += 1

        return revenge_count

    def _detect_overtrading(self) -> List[str]:
        """Phát hiện các ngày overtrading (>10 trades/day)"""
        if self.df.empty:
            return []

        self.df['date'] = self.df['time'].dt.date
        daily_counts = self.df.groupby('date').size()
        overtrading_days = daily_counts[daily_counts > 10].index.tolist()

        return [str(day) for day in overtrading_days]

    def generate_report(self) -> str:
        """Tạo báo cáo tổng hợp"""
        summary = self.get_summary_stats()
        symbol_perf = self.get_symbol_performance()
        time_analysis = self.get_time_based_analysis()
        patterns = self.identify_patterns()

        report = f"""
═══════════════════════════════════════════════════════════
         📊 TRADE HISTORY ANALYSIS REPORT
═══════════════════════════════════════════════════════════

🔢 OVERALL STATISTICS:
  • Total Trades: {summary.get('total_trades', 0)}
  • Win Rate: {summary.get('win_rate', 0)}%
  • Total Profit: ${summary.get('total_profit', 0)}
  • Average Win: ${summary.get('avg_profit', 0)}
  • Average Loss: ${summary.get('avg_loss', 0)}
  • Risk/Reward Ratio: {summary.get('risk_reward_ratio', 0)}:1

📈 TRADE DIRECTION:
  • Long: {summary.get('long_trades', 0)} ({summary.get('long_percentage', 0)}%)
  • Short: {summary.get('short_trades', 0)} ({100 - summary.get('long_percentage', 0)}%)

⏰ BEST TRADING HOURS:
  • {', '.join([f'{h}:00' for h in time_analysis.get('best_trading_hours', [])])}

⚠️ PATTERNS DETECTED:
  • Max Consecutive Wins: {patterns.get('consecutive_wins', 0)}
  • Max Consecutive Losses: {patterns.get('consecutive_losses', 0)}
  • Revenge Trading Instances: {patterns.get('revenge_trading', 0)}
  • Overtrading Days: {len(patterns.get('overtrading_days', []))}

═══════════════════════════════════════════════════════════
        """

        return report
