#!/usr/bin/env python3
"""
DEMO: Phân tích lệnh SHORT với mock data
Minh họa cách bot sẽ phân tích khi có trade history thật
"""

import pandas as pd
from datetime import datetime, timedelta
import random

# Mock SHORT trade data (ví dụ)
mock_short_trades = []

# Generate 50 mock SHORT trades trong 30 ngày
base_time = datetime.now() - timedelta(days=30)

for i in range(50):
    # Random entry price BTC
    entry_price = random.uniform(95000, 105000)

    # Random profit/loss
    is_win = random.random() < 0.65  # 65% win rate
    if is_win:
        # Profitable SHORT: giá giảm
        profit_pct = random.uniform(1, 8)  # 1-8% profit
        exit_price = entry_price * (1 - profit_pct/100)
        profit = random.uniform(50, 500)
    else:
        # Losing SHORT: giá tăng
        loss_pct = random.uniform(1, 4)  # 1-4% loss
        exit_price = entry_price * (1 + loss_pct/100)
        profit = -random.uniform(20, 200)

    # Random time
    trade_time = base_time + timedelta(
        days=random.randint(0, 30),
        hours=random.randint(0, 23)
    )

    trade = {
        'orderId': f'ORDER_{i+1}',
        'symbol': 'BTC-USDT',
        'side': 'SELL',  # SHORT
        'positionSide': 'SHORT',
        'type': 'MARKET',
        'avgPrice': entry_price,
        'price': entry_price,
        'origQty': random.uniform(0.01, 0.1),
        'executedQty': random.uniform(0.01, 0.1),
        'profit': profit,
        'stopLoss': entry_price * (1 + 0.02),  # SL +2%
        'takeProfit': entry_price * (1 - 0.04),  # TP -4%
        'time': int(trade_time.timestamp() * 1000),
        'updateTime': int(trade_time.timestamp() * 1000),
        'status': 'FILLED'
    }

    mock_short_trades.append(trade)

# Sort by time
mock_short_trades.sort(key=lambda x: x['time'])

print("=" * 80)
print("  📊 DEMO: PHÂN TÍCH LỆNH SHORT - Mock Data Analysis")
print("=" * 80)
print()
print(f"📝 Mock data: {len(mock_short_trades)} lệnh SHORT trong 30 ngày")
print()

# Analyze
df = pd.DataFrame(mock_short_trades)

# Convert to numeric
for col in ['avgPrice', 'profit', 'origQty', 'stopLoss', 'takeProfit']:
    df[col] = pd.to_numeric(df[col], errors='coerce')

# Statistics
profitable = df[df['profit'] > 0]
losing = df[df['profit'] < 0]

win_rate = len(profitable) / len(df) * 100
avg_profit = profitable['profit'].mean()
avg_loss = abs(losing['profit'].mean())
total_profit = df['profit'].sum()

print("=" * 80)
print("  📈 TỔNG QUAN")
print("=" * 80)
print(f"\n✅ Lệnh SHORT thắng: {len(profitable)}/{len(df)} ({win_rate:.1f}%)")
print(f"❌ Lệnh SHORT thua: {len(losing)}/{len(df)} ({100-win_rate:.1f}%)")
print(f"\n💰 Tổng Profit: ${total_profit:.2f}")
print(f"📊 Avg Profit (wins): ${avg_profit:.2f}")
print(f"📉 Avg Loss (losses): ${avg_loss:.2f}")
print(f"⚖️ Risk/Reward: 1:{avg_profit/avg_loss:.2f}" if avg_loss > 0 else "")

# Time analysis
df['hour'] = pd.to_datetime(df['time'], unit='ms').dt.hour
df['is_win'] = df['profit'] > 0

# Win rate by hour
hourly_stats = df.groupby('hour').agg({
    'profit': ['count', 'sum'],
    'is_win': 'mean'
})

hourly_stats.columns = ['trades', 'total_profit', 'win_rate']
hourly_stats['win_rate'] = (hourly_stats['win_rate'] * 100).round(1)
hourly_stats = hourly_stats.sort_values('win_rate', ascending=False)

print("\n" + "=" * 80)
print("  ⏰ PHÂN TÍCH THEO GIỜ (Top 5 giờ tốt nhất)")
print("=" * 80)
print()
print(hourly_stats.head(5).to_string())

# Profit distribution
small = profitable[profitable['profit'] < 100]
medium = profitable[(profitable['profit'] >= 100) & (profitable['profit'] < 300)]
large = profitable[profitable['profit'] >= 300]

print("\n" + "=" * 80)
print("  💵 PHÂN BỐ PROFIT")
print("=" * 80)
print(f"\n💚 Profit nhỏ (<$100): {len(small)} lệnh - Avg ${small['profit'].mean():.2f}")
print(f"💛 Profit trung bình ($100-$300): {len(medium)} lệnh - Avg ${medium['profit'].mean():.2f}")
print(f"💙 Profit lớn (>$300): {len(large)} lệnh - Avg ${large['profit'].mean():.2f}")

# Entry price analysis
print("\n" + "=" * 80)
print("  🎯 PHÂN TÍCH ĐIỂM VÀO LỆNH SHORT")
print("=" * 80)

# Profitable SHORTs
profitable_copy = profitable.copy()
profitable_copy['profit_pct'] = (profitable_copy['profit'] / (profitable_copy['avgPrice'] * profitable_copy['origQty'])) * 100

print(f"\n✅ LỆNH SHORT THÀNH CÔNG:")
print(f"   • Entry price trung bình: ${profitable['avgPrice'].mean():.2f}")
print(f"   • Entry price thấp nhất: ${profitable['avgPrice'].min():.2f}")
print(f"   • Entry price cao nhất: ${profitable['avgPrice'].max():.2f}")
print(f"   • Profit % trung bình: {profitable_copy['profit_pct'].mean():.2f}%")

# Find best entry zones
entry_bins = pd.qcut(profitable['avgPrice'], q=3, labels=['Low Zone', 'Mid Zone', 'High Zone'], duplicates='drop')
profitable['entry_zone'] = entry_bins

zone_stats = profitable.groupby('entry_zone').agg({
    'profit': ['count', 'mean', 'sum']
})

print(f"\n📊 ENTRY ZONES (Profitable Shorts):")
for zone in profitable['entry_zone'].unique():
    zone_trades = profitable[profitable['entry_zone'] == zone]
    avg_entry = zone_trades['avgPrice'].mean()
    avg_profit = zone_trades['profit'].mean()
    count = len(zone_trades)

    print(f"   • {zone}: Entry ~${avg_entry:.0f} | {count} trades | Avg profit ${avg_profit:.2f}")

# Stop Loss / Take Profit analysis
print("\n" + "=" * 80)
print("  🛑 PHÂN TÍCH STOP LOSS & TAKE PROFIT")
print("=" * 80)

profitable['sl_distance_%'] = abs((profitable['stopLoss'] - profitable['avgPrice']) / profitable['avgPrice'] * 100)
profitable['tp_distance_%'] = abs((profitable['takeProfit'] - profitable['avgPrice']) / profitable['avgPrice'] * 100)

print(f"\n✅ Lệnh SHORT thành công:")
print(f"   • SL distance trung bình: {profitable['sl_distance_%'].mean():.2f}%")
print(f"   • TP distance trung bình: {profitable['tp_distance_%'].mean():.2f}%")
print(f"   • R:R ratio: 1:{(profitable['tp_distance_%'].mean() / profitable['sl_distance_%'].mean()):.2f}")

# Recommendations
print("\n" + "=" * 80)
print("  💡 KHUYẾN NGHỊ CHIẾN LƯỢC SHORT")
print("=" * 80)

best_hours = hourly_stats.head(3).index.tolist()
best_zone = profitable.groupby('entry_zone')['profit'].mean().idxmax()
ideal_sl = profitable['sl_distance_%'].median()
ideal_tp = profitable['tp_distance_%'].median()

print(f"\n✨ Dựa trên phân tích {len(profitable)} lệnh SHORT thành công:")
print(f"\n⏰ Khung giờ tốt nhất:")
for hour in best_hours:
    print(f"   • {hour}:00 - {hourly_stats.loc[hour, 'win_rate']:.1f}% win rate")

print(f"\n🎯 Entry Zone tốt nhất: {best_zone}")
print(f"   → Vào lệnh SHORT khi giá ở vùng này có tỷ lệ thắng cao nhất")

print(f"\n🛑 Stop Loss khuyến nghị: {ideal_sl:.1f}%")
print(f"   → Set SL cách entry khoảng {ideal_sl:.1f}% để bảo vệ vốn")

print(f"\n🎯 Take Profit khuyến nghị:")
print(f"   → TP1: {ideal_tp/2:.1f}% (chốt 50% position)")
print(f"   → TP2: {ideal_tp:.1f}% (chốt 50% còn lại)")

print(f"\n⚖️ Risk/Reward tối ưu: 1:{ideal_tp/ideal_sl:.1f}")

print("\n" + "=" * 80)
print("  🎓 CHIẾN THUẬT VÀO LỆNH SHORT")
print("=" * 80)

print("""
📝 SETUP IDEAL CHO SHORT:

1. ⏰ TIMING:
   • Trade trong khung giờ có win rate cao
   • Tránh khung giờ thị trường biến động mạnh bất thường

2. 🎯 ENTRY SIGNALS:
   • Giá chạm vùng kháng cự (resistance)
   • RSI > 70 (overbought)
   • MACD xuất hiện tín hiệu bearish crossover
   • Giá dưới EMA 50

3. 🛡️ RISK MANAGEMENT:
   • Position size: 1-2% account mỗi lệnh
   • Stop Loss: +2% từ entry
   • Take Profit: -2% (TP1), -4% (TP2)

4. ✅ CONFIRMATION:
   • Đợi nến xác nhận (không vào ngay đầu nến)
   • Volume tăng khi giá đảo chiều
   • Trend tổng thể đang downtrend hoặc sideways

5. ❌ TRÁNH:
   • SHORT trong uptrend mạnh
   • Vào lệnh khi không có confirmation
   • Không set SL (rất nguy hiểm!)
   • Overtrading (quá nhiều lệnh/ngày)
""")

print("\n" + "=" * 80)
print("  ✨ KẾT LUẬN")
print("=" * 80)

print(f"""
Với win rate {win_rate:.1f}% và R:R ratio trung bình 1:{avg_profit/avg_loss:.1f},
chiến lược SHORT của bạn cho thấy tiềm năng tốt.

🔑 ĐIỂM MẠNH:
• Win rate >{win_rate:.0f}% cho thấy khả năng đọc trend tốt
• Average profit cao hơn average loss
• Risk management ổn định với SL/TP rõ ràng

💡 CẦN CẢI THIỆN:
• Tăng position size ở những setup có confidence cao
• Tập trung trade trong best hours
• Theo dõi và tránh revenge trading

🤖 BOT SẼ GIÚP BẠN:
• Tự động phân tích trade history thật của bạn
• Tìm patterns thành công của riêng bạn
• Gửi tín hiệu khi có setup phù hợp với style của bạn
• Nhắc nhở về risk management
""")

print("\n" + "=" * 80)
