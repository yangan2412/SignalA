#!/usr/bin/env python3
"""
Phân tích THẬT các lệnh SHORT từ Standard Futures
"""

import hmac
import hashlib
import time
import requests
import json
from datetime import datetime
import pandas as pd

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

print("=" * 80)
print("  📊 PHÂN TÍCH LỆNH SHORT THẬT - Standard Futures")
print("=" * 80)
print()

# Get all orders
params = {'timestamp': int(time.time() * 1000)}
signature = generate_signature(params, SECRET_KEY)
params['signature'] = signature
headers = {'X-BX-APIKEY': API_KEY}

url = f"{BASE_URL}/openApi/contract/v1/allOrders"
response = requests.get(url, params=params, headers=headers)

data = response.json()

if data.get('code') != 0:
    print(f"❌ Error: {data.get('msg')}")
    exit(1)

all_orders = data.get('data', [])
print(f"✅ Lấy được {len(all_orders)} lệnh tổng cộng\n")

# Filter SHORT only
short_orders = [o for o in all_orders if o.get('positionSide') == 'SHORT']
long_orders = [o for o in all_orders if o.get('positionSide') == 'LONG']

print(f"📊 Tổng quan:")
print(f"   • SHORT: {len(short_orders)} lệnh")
print(f"   • LONG: {len(long_orders)} lệnh")
print()

if not short_orders:
    print("⚠️ Không có lệnh SHORT!")
    exit(0)

print("=" * 80)
print("  🔍 CHI TIẾT CÁC LỆNH SHORT")
print("=" * 80)
print()

# Analyze each SHORT
for idx, order in enumerate(short_orders, 1):
    entry_time = datetime.fromtimestamp(order['time'] / 1000)
    close_time = datetime.fromtimestamp(order['updateTime'] / 1000)
    duration = (order['updateTime'] - order['time']) / 1000 / 3600  # hours

    entry_price = order['avgPrice']
    close_price = order['closePrice']
    price_change_pct = ((close_price - entry_price) / entry_price) * 100

    # Calculate profit
    # SHORT profit: (entry - close) * quantity
    position_value = order['cumQuote']  # USDT value
    quantity = order['executedQty']
    leverage = order['leverage']
    margin = order['margin']

    # PnL calculation for SHORT
    pnl = (entry_price - close_price) * quantity
    pnl_pct = (pnl / margin) * 100

    print(f"SHORT #{idx}:")
    print(f"   📅 Thời gian:")
    print(f"      • Vào lệnh: {entry_time.strftime('%Y-%m-%d %H:%M')}")
    print(f"      • Đóng lệnh: {close_time.strftime('%Y-%m-%d %H:%M')}")
    print(f"      • Giữ lệnh: {duration:.1f} giờ ({duration/24:.1f} ngày)")
    print()
    print(f"   💰 Giao dịch:")
    print(f"      • Entry Price: ${entry_price:.5f}")
    print(f"      • Close Price: ${close_price:.5f}")
    print(f"      • Price Change: {price_change_pct:+.2f}%")
    print(f"      • Quantity: {quantity:.4f}")
    print(f"      • Position Value: ${position_value:.2f}")
    print()
    print(f"   ⚙️ Setup:")
    print(f"      • Leverage: {leverage:.0f}x")
    print(f"      • Margin: ${margin:.2f}")
    print()
    print(f"   📈 Kết quả:")
    print(f"      • PnL: ${pnl:+.2f}")
    print(f"      • ROI: {pnl_pct:+.2f}% (trên margin)")
    if pnl > 0:
        print(f"      • ✅ THẮNG")
    else:
        print(f"      • ❌ THUA")
    print()
    print(f"   {'-' * 76}")
    print()

# Summary statistics
print("=" * 80)
print("  📊 PHÂN TÍCH TỔNG HỢP SHORT TRADES")
print("=" * 80)
print()

df = pd.DataFrame(short_orders)

# Calculate PnL for each
df['entry_price'] = df['avgPrice'].astype(float)
df['close_price'] = df['closePrice'].astype(float)
df['quantity'] = df['executedQty'].astype(float)
df['margin'] = df['margin'].astype(float)
df['leverage'] = df['leverage'].astype(float)

# PnL = (entry - close) * quantity for SHORT
df['pnl'] = (df['entry_price'] - df['close_price']) * df['quantity']
df['pnl_pct'] = (df['pnl'] / df['margin']) * 100
df['price_change_pct'] = ((df['close_price'] - df['entry_price']) / df['entry_price']) * 100

# Duration
df['duration_hours'] = (df['updateTime'] - df['time']) / 1000 / 3600

profitable = df[df['pnl'] > 0]
losing = df[df['pnl'] < 0]

print(f"✅ Lệnh SHORT thắng: {len(profitable)}/{len(df)}")
print(f"❌ Lệnh SHORT thua: {len(losing)}/{len(df)}")
print(f"📊 Win Rate: {len(profitable)/len(df)*100:.1f}%")
print()

if len(profitable) > 0:
    print(f"💚 LỆNH THẮNG:")
    print(f"   • Tổng profit: ${profitable['pnl'].sum():+.2f}")
    print(f"   • Avg profit: ${profitable['pnl'].mean():+.2f}")
    print(f"   • ROI trung bình: {profitable['pnl_pct'].mean():+.1f}%")
    print(f"   • Giá giảm trung bình: {profitable['price_change_pct'].mean():.2f}%")
    print(f"   • Thời gian giữ TB: {profitable['duration_hours'].mean():.1f} giờ")
    print()

if len(losing) > 0:
    print(f"❌ LỆNH THUA:")
    print(f"   • Tổng loss: ${losing['pnl'].sum():+.2f}")
    print(f"   • Avg loss: ${abs(losing['pnl'].mean()):+.2f}")
    print(f"   • ROI trung bình: {losing['pnl_pct'].mean():+.1f}%")
    print(f"   • Giá tăng trung bình: {losing['price_change_pct'].mean():+.2f}%")
    print(f"   • Thời gian giữ TB: {losing['duration_hours'].mean():.1f} giờ")
    print()

print(f"📊 OVERALL:")
print(f"   • Net PnL: ${df['pnl'].sum():+.2f}")
print(f"   • Avg leverage: {df['leverage'].mean():.1f}x")
print(f"   • Avg margin: ${df['margin'].mean():.2f}")
print()

# Time analysis
df['hour'] = pd.to_datetime(df['time'], unit='ms').dt.hour
df['day_of_week'] = pd.to_datetime(df['time'], unit='ms').dt.day_name()

print("=" * 80)
print("  ⏰ PHÂN TÍCH THỜI GIAN")
print("=" * 80)
print()

print("📅 Lệnh SHORT theo ngày trong tuần:")
day_stats = df.groupby('day_of_week').agg({
    'pnl': ['count', 'sum', 'mean']
}).round(2)
print(day_stats)
print()

print("🕐 Lệnh SHORT theo giờ trong ngày:")
hour_stats = df.groupby('hour').agg({
    'pnl': ['count', 'sum', 'mean']
}).round(2)
print(hour_stats)
print()

# Best setups
print("=" * 80)
print("  💡 INSIGHTS & KHUYẾN NGHỊ")
print("=" * 80)
print()

if len(profitable) > 0:
    avg_win = profitable['pnl'].mean()
    avg_loss = abs(losing['pnl'].mean()) if len(losing) > 0 else 0
    risk_reward = avg_win / avg_loss if avg_loss > 0 else 0

    print(f"✨ Chiến lược SHORT của bạn:")
    print(f"   • Win rate: {len(profitable)/len(df)*100:.1f}%")
    print(f"   • Risk/Reward: 1:{risk_reward:.2f}")
    print(f"   • Avg leverage: {df['leverage'].mean():.0f}x")
    print()

    print(f"🎯 ĐIỂM MẠNH:")
    if len(profitable)/len(df) > 0.6:
        print(f"   ✓ Win rate tốt (>{len(profitable)/len(df)*100:.0f}%)")
    if risk_reward > 1.5:
        print(f"   ✓ R:R ratio khá ({risk_reward:.1f}:1)")
    print()

    print(f"⚠️ CẦN CẢI THIỆN:")
    if len(losing) > 0:
        avg_hold_win = profitable['duration_hours'].mean()
        avg_hold_loss = losing['duration_hours'].mean()
        if avg_hold_loss > avg_hold_win:
            print(f"   • Cắt lỗ nhanh hơn (đang giữ lệnh thua {avg_hold_loss:.0f}h vs thắng {avg_hold_win:.0f}h)")

    print()

print("=" * 80)
print("  🎓 CHIẾN THUẬT VÀO LỆNH SHORT DỰA TRÊN DỮ LIỆU CỦA BẠN")
print("=" * 80)
print()

# Recommendations based on profitable trades
if len(profitable) > 0:
    best_leverage = profitable['leverage'].mode()[0] if len(profitable['leverage'].mode()) > 0 else profitable['leverage'].mean()
    best_margin = profitable['margin'].median()

    print(f"📝 SETUP KHUYẾN NGHỊ:")
    print(f"   • Leverage: {best_leverage:.0f}x (dựa trên lệnh thắng của bạn)")
    print(f"   • Margin: ~${best_margin:.0f} USDT")
    print(f"   • Target: {abs(profitable['price_change_pct'].mean()):.1f}% giảm giá")
    print()

    print(f"⏰ TIMING:")
    if not hour_stats.empty:
        best_hour = hour_stats[('pnl', 'mean')].idxmax()
        print(f"   • Giờ tốt nhất: {best_hour}:00")
    print()

print("🤖 BOT SẼ:")
print("   • Monitor các coin bạn đã trade")
print("   • Phát hiện setup tương tự lệnh thắng của bạn")
print("   • Gửi tín hiệu qua Telegram")
print("   • Nhắc về SL/TP dựa trên thống kê")
print()

print("=" * 80)
