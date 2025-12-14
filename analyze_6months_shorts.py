#!/usr/bin/env python3
"""
Phân tích TOÀN BỘ lệnh SHORT trong 6 tháng
Đánh giá chiến thuật và risk
"""

import hmac
import hashlib
import time
import requests
import json
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

API_KEY = "K5tdJ7lJ7e45gF0r9T0OOsHQrdyg0XGHrZ6vT5CQ8DFriubLnHCyH8kxd3zb8sw2b8qBm2l2tq9fbYIPrNQ9w"
SECRET_KEY = "aSMSk0rwMALgF7M3yk3lnXQ9pVAiMZj3Qmh7YsMmG8NQCmuW8ebJ2Jbr0ROv23aJ4y2tUObjn3v0YHYYkkg"
BASE_URL = "https://open-api.bingx.com"

def generate_signature(params, secret):
    query_string = '&'.join([f"{k}={params[k]}" for k in sorted(params.keys())])
    signature = hmac.new(
        secret.encode('utf-8'),
        query_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return signature

def get_all_orders():
    """Get all orders from Standard Futures"""
    params = {
        'timestamp': int(time.time() * 1000)
    }

    signature = generate_signature(params, SECRET_KEY)
    params['signature'] = signature
    headers = {'X-BX-APIKEY': API_KEY}

    url = f"{BASE_URL}/openApi/contract/v1/allOrders"
    response = requests.get(url, params=params, headers=headers)

    data = response.json()

    if data.get('code') != 0:
        print(f"❌ Error: {data.get('msg')}")
        return []

    return data.get('data', [])

print("=" * 80)
print("  📊 PHÂN TÍCH LỆNH SHORT 6 THÁNG - ĐÁNH GIÁ RISK")
print("=" * 80)
print()

# Calculate 6 months ago
six_months_ago = int((datetime.now() - timedelta(days=180)).timestamp() * 1000)
now = int(datetime.now().timestamp() * 1000)

print(f"📅 Lấy toàn bộ lịch sử giao dịch...")
print()

# Get all orders
all_orders = get_all_orders()

# Filter by time (6 months)
print(f"🔍 Lọc lệnh từ {datetime.fromtimestamp(six_months_ago/1000).strftime('%Y-%m-%d')} đến nay...")
all_orders = [o for o in all_orders if o.get('time', 0) >= six_months_ago]

print(f"✅ Lấy được {len(all_orders)} lệnh tổng cộng")
print()

# Filter SHORT only
short_orders = [o for o in all_orders if o.get('positionSide') == 'SHORT']
long_orders = [o for o in all_orders if o.get('positionSide') == 'LONG']

print(f"📊 Tổng quan 6 tháng:")
print(f"   • LONG: {len(long_orders)} lệnh")
print(f"   • SHORT: {len(short_orders)} lệnh")
if len(short_orders) + len(long_orders) > 0:
    print(f"   • Tỷ lệ SHORT/LONG: {len(short_orders)/(len(long_orders)+len(short_orders))*100:.1f}%")
print()

if len(short_orders) == 0:
    print("⚠️ Không có lệnh SHORT trong 6 tháng!")
    exit(0)

# Convert to DataFrame
df = pd.DataFrame(short_orders)

# Data processing
df['entry_price'] = df['avgPrice'].astype(float)
df['close_price'] = df['closePrice'].astype(float)
df['quantity'] = df['executedQty'].astype(float)
df['margin'] = df['margin'].astype(float)
df['leverage'] = df['leverage'].astype(float)
df['position_value'] = df['cumQuote'].astype(float)

# Calculate PnL (SHORT: entry - close)
df['pnl'] = (df['entry_price'] - df['close_price']) * df['quantity']
df['pnl_pct'] = (df['pnl'] / df['margin']) * 100
df['price_change_pct'] = ((df['close_price'] - df['entry_price']) / df['entry_price']) * 100

# Time analysis
df['entry_time'] = pd.to_datetime(df['time'], unit='ms')
df['close_time'] = pd.to_datetime(df['updateTime'], unit='ms')
df['duration_hours'] = (df['updateTime'] - df['time']) / 1000 / 3600
df['duration_days'] = df['duration_hours'] / 24

df['hour'] = df['entry_time'].dt.hour
df['day_of_week'] = df['entry_time'].dt.day_name()
df['month'] = df['entry_time'].dt.strftime('%Y-%m')

# Sort by time
df = df.sort_values('entry_time')

# Win/Loss
df['is_win'] = df['pnl'] > 0

profitable = df[df['is_win']]
losing = df[~df['is_win']]

print("=" * 80)
print("  📈 PHÂN TÍCH TỔNG QUAN")
print("=" * 80)
print()

win_rate = len(profitable) / len(df) * 100

print(f"🎯 KẾT QUẢ:")
print(f"   • Tổng số lệnh SHORT: {len(df)}")
print(f"   • Lệnh thắng: {len(profitable)}")
print(f"   • Lệnh thua: {len(losing)}")
print(f"   • Win Rate: {win_rate:.1f}%")
print()

print(f"💰 PROFIT & LOSS:")
print(f"   • Tổng PnL: ${df['pnl'].sum():+.2f}")
print(f"   • Avg PnL/trade: ${df['pnl'].mean():+.2f}")
print(f"   • Max win: ${df['pnl'].max():+.2f}")
print(f"   • Max loss: ${df['pnl'].min():+.2f}")
print()

if len(profitable) > 0 and len(losing) > 0:
    avg_win = profitable['pnl'].mean()
    avg_loss = abs(losing['pnl'].mean())
    risk_reward = avg_win / avg_loss if avg_loss > 0 else 0

    print(f"📊 RISK/REWARD:")
    print(f"   • Avg Win: ${avg_win:+.2f}")
    print(f"   • Avg Loss: ${avg_loss:+.2f}")
    print(f"   • Risk/Reward: 1:{risk_reward:.2f}")
    print()

print(f"⚙️ TRADING STYLE:")
print(f"   • Avg Leverage: {df['leverage'].mean():.1f}x")
print(f"   • Avg Margin: ${df['margin'].mean():.2f}")
print(f"   • Avg Position Value: ${df['position_value'].mean():.2f}")
print(f"   • Avg Hold Time: {df['duration_hours'].mean():.1f} giờ ({df['duration_days'].mean():.1f} ngày)")
print()

# Risk Analysis
print("=" * 80)
print("  ⚠️ ĐÁNH GIÁ RISK")
print("=" * 80)
print()

# 1. Consecutive losses
max_consecutive_loss = 0
current_streak = 0
for is_win in df['is_win']:
    if not is_win:
        current_streak += 1
        max_consecutive_loss = max(max_consecutive_loss, current_streak)
    else:
        current_streak = 0

# 2. Max drawdown
cumulative_pnl = df['pnl'].cumsum()
running_max = cumulative_pnl.cummax()
drawdown = cumulative_pnl - running_max
max_drawdown = drawdown.min()

# 3. Loss distribution
if len(losing) > 0:
    loss_std = losing['pnl'].std()
    worst_10pct = losing['pnl'].quantile(0.1)  # 10% worst losses

print(f"🔴 RỦI RO:")
print(f"   • Max Consecutive Losses: {max_consecutive_loss} lệnh")
print(f"   • Max Drawdown: ${max_drawdown:.2f}")
print(f"   • Worst Single Loss: ${df['pnl'].min():.2f}")

if len(losing) > 0:
    print(f"   • 10% worst losses avg: ${worst_10pct:.2f}")
    print(f"   • Loss volatility (std): ${loss_std:.2f}")

print()

# Risk level assessment
risk_level = "THẤP"
risk_score = 0

if max_consecutive_loss >= 5:
    risk_score += 2
elif max_consecutive_loss >= 3:
    risk_score += 1

if win_rate < 50:
    risk_score += 2
elif win_rate < 60:
    risk_score += 1

if len(losing) > 0:
    if abs(df['pnl'].min()) > df['margin'].mean() * 2:
        risk_score += 2

if risk_score >= 4:
    risk_level = "CAO"
elif risk_score >= 2:
    risk_level = "TRUNG BÌNH"

print(f"📊 MỨC ĐỘ RỦI RO: {risk_level}")
print()

# Monthly performance
print("=" * 80)
print("  📅 HIỆU SUẤT THEO THÁNG")
print("=" * 80)
print()

monthly_stats = df.groupby('month').agg({
    'pnl': ['count', 'sum', 'mean'],
    'is_win': 'mean'
}).round(2)

monthly_stats.columns = ['trades', 'total_pnl', 'avg_pnl', 'win_rate']
monthly_stats['win_rate'] = (monthly_stats['win_rate'] * 100).round(1)

print(monthly_stats.to_string())
print()

# Best and worst month
best_month = monthly_stats['total_pnl'].idxmax()
worst_month = monthly_stats['total_pnl'].idxmin()

print(f"✅ Tháng tốt nhất: {best_month} (${monthly_stats.loc[best_month, 'total_pnl']:+.2f})")
print(f"❌ Tháng tệ nhất: {worst_month} (${monthly_stats.loc[worst_month, 'total_pnl']:+.2f})")
print()

# Time patterns
print("=" * 80)
print("  ⏰ PATTERNS THEO THỜI GIAN")
print("=" * 80)
print()

# Day of week
dow_stats = df.groupby('day_of_week').agg({
    'pnl': ['count', 'sum', 'mean'],
    'is_win': 'mean'
}).round(2)

dow_stats.columns = ['trades', 'total_pnl', 'avg_pnl', 'win_rate']
dow_stats['win_rate'] = (dow_stats['win_rate'] * 100).round(1)
dow_stats = dow_stats.sort_values('win_rate', ascending=False)

print("📅 Win Rate theo ngày:")
print(dow_stats[['trades', 'win_rate']].to_string())
print()

# Hour of day
hour_stats = df.groupby('hour').agg({
    'pnl': ['count', 'sum', 'mean'],
    'is_win': 'mean'
}).round(2)

hour_stats.columns = ['trades', 'total_pnl', 'avg_pnl', 'win_rate']
hour_stats['win_rate'] = (hour_stats['win_rate'] * 100).round(1)
hour_stats = hour_stats.sort_values('win_rate', ascending=False)

print("🕐 Top 5 giờ tốt nhất:")
print(hour_stats.head(5)[['trades', 'win_rate', 'avg_pnl']].to_string())
print()

# Detailed winning trades analysis
print("=" * 80)
print("  ✅ PHÂN TÍCH LỆNH THẮNG")
print("=" * 80)
print()

if len(profitable) > 0:
    print(f"📊 Lệnh thắng ({len(profitable)} lệnh):")
    print(f"   • Avg profit: ${profitable['pnl'].mean():+.2f}")
    print(f"   • Avg ROI: {profitable['pnl_pct'].mean():+.1f}%")
    print(f"   • Giá giảm TB: {profitable['price_change_pct'].mean():.2f}%")
    print(f"   • Hold time TB: {profitable['duration_hours'].mean():.1f}h")
    print(f"   • Avg leverage: {profitable['leverage'].mean():.1f}x")
    print()

    # Best setups
    top_profitable = profitable.nlargest(3, 'pnl')
    print("🏆 Top 3 lệnh lời nhất:")
    for idx, trade in enumerate(top_profitable.itertuples(), 1):
        print(f"   #{idx}: Entry ${trade.entry_price:.5f} → ${trade.close_price:.5f} "
              f"({trade.price_change_pct:.1f}%) = ${trade.pnl:+.2f} "
              f"({trade.duration_days:.1f} ngày)")
    print()

# Detailed losing trades analysis
if len(losing) > 0:
    print("=" * 80)
    print("  ❌ PHÂN TÍCH LỆNH THUA")
    print("=" * 80)
    print()

    print(f"📊 Lệnh thua ({len(losing)} lệnh):")
    print(f"   • Avg loss: ${losing['pnl'].mean():+.2f}")
    print(f"   • Avg ROI: {losing['pnl_pct'].mean():+.1f}%")
    print(f"   • Giá tăng TB: {losing['price_change_pct'].mean():+.2f}%")
    print(f"   • Hold time TB: {losing['duration_hours'].mean():.1f}h")
    print(f"   • Avg leverage: {losing['leverage'].mean():.1f}x")
    print()

    # Worst trades
    worst_trades = losing.nsmallest(3, 'pnl')
    print("⚠️ Top 3 lệnh lỗ nhất:")
    for idx, trade in enumerate(worst_trades.itertuples(), 1):
        print(f"   #{idx}: Entry ${trade.entry_price:.5f} → ${trade.close_price:.5f} "
              f"({trade.price_change_pct:+.1f}%) = ${trade.pnl:.2f} "
              f"({trade.duration_days:.1f} ngày)")
    print()

    # Why losing?
    print("🔍 NGUYÊN NHÂN THUA:")

    # Compare hold time
    avg_win_hold = profitable['duration_hours'].mean() if len(profitable) > 0 else 0
    avg_loss_hold = losing['duration_hours'].mean()

    if avg_loss_hold > avg_win_hold * 1.5:
        print(f"   ⚠️ Giữ lệnh thua quá lâu ({avg_loss_hold:.0f}h vs {avg_win_hold:.0f}h thắng)")

    # Compare leverage
    avg_win_lev = profitable['leverage'].mean() if len(profitable) > 0 else 0
    avg_loss_lev = losing['leverage'].mean()

    if avg_loss_lev > avg_win_lev * 1.2:
        print(f"   ⚠️ Leverage cao hơn khi thua ({avg_loss_lev:.0f}x vs {avg_win_lev:.0f}x thắng)")

    # Early vs late month
    losing['day_of_month'] = losing['entry_time'].dt.day
    if losing['day_of_month'].mean() > 20:
        print(f"   ⚠️ Hay thua vào cuối tháng (avg day {losing['day_of_month'].mean():.0f})")

    print()

# Final recommendations
print("=" * 80)
print("  💡 CHIẾN THUẬT & KHUYẾN NGHỊ")
print("=" * 80)
print()

print(f"🎯 CHIẾN THUẬT SHORT DỰA TRÊN {len(df)} LỆNH:")
print()

# Entry strategy
if len(profitable) > 0:
    best_hour = hour_stats.head(1).index[0]
    best_day = dow_stats.head(1).index[0]
    optimal_leverage = round(profitable['leverage'].median())
    optimal_margin = round(profitable['margin'].median(), 0)
    target_drop = abs(profitable['price_change_pct'].median())

    print(f"📍 ENTRY SETUP:")
    print(f"   • Giờ vào tốt nhất: {best_hour}:00")
    print(f"   • Ngày vào tốt nhất: {best_day}")
    print(f"   • Leverage khuyến nghị: {optimal_leverage}x")
    print(f"   • Margin khuyến nghị: ${optimal_margin}")
    print(f"   • Target giảm giá: {target_drop:.1f}%")
    print()

    print(f"🛑 EXIT SETUP:")
    print(f"   • Take Profit: {target_drop:.1f}% giảm")

    if len(losing) > 0:
        safe_sl = abs(losing['price_change_pct'].quantile(0.75))  # 75% losses are smaller than this
        print(f"   • Stop Loss: +{safe_sl:.1f}% tăng")

    avg_hold = profitable['duration_hours'].median()
    print(f"   • Thời gian giữ: ~{avg_hold:.0f}h")
    print()

print(f"⚠️ QUẢN LÝ RỦI RO:")
print(f"   • Max consecutive loss: {max_consecutive_loss} lệnh")
if max_consecutive_loss >= 3:
    print(f"   → NGUY HIỂM: Dừng trade sau {max_consecutive_loss} lệnh thua liên tiếp!")

if abs(max_drawdown) > df['margin'].mean() * 5:
    print(f"   • Max drawdown lớn (${abs(max_drawdown):.2f})")
    print(f"   → Giảm leverage hoặc position size!")

if len(losing) > 0 and avg_loss_hold > avg_win_hold * 1.5:
    print(f"   • Cắt lỗ nhanh hơn (đang giữ {avg_loss_hold:.0f}h khi thua)")

print()

print(f"✅ KẾT LUẬN:")
if win_rate >= 60 and risk_level == "THẤP":
    print(f"   🎉 Chiến thuật SHORT của bạn RẤT TỐT!")
    print(f"   • Win rate {win_rate:.0f}% với risk {risk_level}")
    print(f"   • Có thể tăng position size")
elif win_rate >= 50:
    print(f"   ✅ Chiến thuật SHORT khá ổn")
    print(f"   • Win rate {win_rate:.0f}% với risk {risk_level}")
    print(f"   • Cần cải thiện exit strategy")
else:
    print(f"   ⚠️ Chiến thuật cần cải thiện")
    print(f"   • Win rate chỉ {win_rate:.0f}%")
    print(f"   • Tập trung vào best setups")

print()
print("=" * 80)
