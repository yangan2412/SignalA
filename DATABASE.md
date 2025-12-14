# 🗄️ DATABASE DESIGN - SignalA Trading Bot

## 📊 Database Schema

### 1. **user_trades** - Lịch sử giao dịch thực tế
Lưu tất cả trades của user từ BingX (import từ CSV hoặc API).

```sql
- id (PK)
- order_id (unique)
- symbol (BTC-USDT, ETH-USDT...)
- position_side (LONG/SHORT)
- entry_price, close_price, avg_price
- quantity, margin, leverage
- profit, profit_pct
- stop_loss, take_profit
- entry_time, close_time
- status
- notes
```

**Mục đích:**
- Phân tích pattern của user
- So sánh với bot performance
- Historical analysis

---

### 2. **bot_signals** - Tín hiệu bot đã gửi
Mỗi lần bot gửi signal sẽ tạo 1 record.

```sql
- id (PK)
- symbol
- direction (LONG/SHORT)
- entry_price
- stop_loss, take_profit_1, take_profit_2
- confidence (0-1)
- strategy_name
- rsi, macd, ema_50, ema_200 (indicators tại thời điểm signal)
- signal_time
- status (PENDING/ACTIVE/CLOSED)
- telegram_message_id, chat_id
```

**Mục đích:**
- Track tất cả signals đã gửi
- Link với results để đánh giá
- Audit trail

---

### 3. **signal_results** - Kết quả của mỗi signal
Sau khi signal đóng (hit TP/SL/expired), lưu kết quả.

```sql
- id (PK)
- signal_id (FK → bot_signals)
- outcome (HIT_TP1/HIT_TP2/HIT_SL/EXPIRED)
- actual_entry_price, actual_exit_price
- theoretical_pnl, theoretical_pnl_pct
- entry_time, exit_time, duration_hours
- max_price_reached, min_price_reached
- is_win (boolean)
- notes
```

**Mục đích:**
- **ĐỐI SOÁT**: So sánh signal vs kết quả thực tế
- Calculate win rate, avg PnL
- Identify best/worst signals

---

### 4. **signal_price_updates** - Tracking giá real-time
Update giá mỗi phút cho active signals.

```sql
- id (PK)
- signal_id (FK → bot_signals)
- current_price
- price_change_pct
- distance_to_sl_pct, distance_to_tp1_pct, distance_to_tp2_pct
- timestamp
```

**Mục đích:**
- Monitor signals real-time
- Determine max/min price reached
- Visualize price movement

---

### 5. **strategies** - Các strategies
Track performance của từng strategy riêng.

```sql
- id (PK)
- name (unique)
- description
- parameters (JSON)
- is_active
- total_signals, winning_signals, losing_signals
- win_rate, total_pnl
```

**Mục đích:**
- Compare strategies
- A/B testing
- Enable/disable strategies

---

### 6. **performance_metrics** - Metrics theo thời gian
Aggregate metrics theo ngày/tuần/tháng.

```sql
- id (PK)
- date
- period_type (DAILY/WEEKLY/MONTHLY)
- signals_sent, signals_won, signals_lost
- win_rate, total_pnl, avg_pnl_per_signal
- max_drawdown, sharpe_ratio
- long_signals, short_signals
- long_win_rate, short_win_rate
```

**Mục đích:**
- Track performance over time
- Identify trends
- Generate reports

---

## 🔄 WORKFLOW

### 1. Import User Trades
```bash
python import_csv.py trades_history.csv
```

### 2. Bot Gửi Signal
```python
# Bot phát hiện setup
signal_data = {
    'symbol': 'BTC-USDT',
    'side': 'SHORT',
    'entry_price': 100000,
    'stop_loss': 102000,
    'take_profit_1': 98000,
    'take_profit_2': 96000,
    'confidence': 0.85,
    'strategy': 'Learned Strategy'
}

# Lưu vào DB
signal = db.create_signal(signal_data)

# Gửi Telegram
bot.send_signal(signal_data)
```

### 3. Signal Tracker Monitor
```python
# Mỗi phút check giá
while True:
    active_signals = db.get_active_signals()

    for signal in active_signals:
        current_price = get_current_price(signal.symbol)

        # Update DB
        db.update_signal_price(signal.id, current_price)

        # Tự động đóng nếu hit TP/SL
        # → Tạo SignalResult
```

### 4. Đối Soát
```python
# Xem performance bot
perf = db.get_bot_performance(days=30)
print(f"Win Rate: {perf['win_rate']}%")
print(f"Total PnL: ${perf['total_pnl']}")

# So sánh bot vs user
comparison = db.compare_bot_vs_user(days=30)
```

---

## 📈 KẾT QUẢ ĐỐI SOÁT

### Report Example:
```
╔════════════════════════════════════════════════════════════╗
║            BOT PERFORMANCE REPORT (30 Days)               ║
╚════════════════════════════════════════════════════════════╝

📊 SIGNALS SENT:
   • Total: 25
   • Won: 18
   • Lost: 7
   • Win Rate: 72%

💰 THEORETICAL PnL:
   • Total: $+450.00
   • Average: $+18.00
   • Best: $+120.00
   • Worst: $-45.00

🆚 VS YOUR ACTUAL TRADES:
   • Your Win Rate: 65%
   • Your Total PnL: $+380.00

✅ Bot performance: +7% better win rate, +18% better PnL
```

---

## 🔍 QUERIES THƯỜNG DÙNG

### Get all winning signals:
```python
winning_signals = session.query(BotSignal).join(SignalResult).filter(
    SignalResult.is_win == True
).all()
```

### Get signals by strategy:
```python
strategy_signals = session.query(BotSignal).filter(
    BotSignal.strategy_name == 'Learned Strategy'
).all()
```

### Get SHORT signals performance:
```python
short_signals = session.query(BotSignal).filter(
    BotSignal.direction == 'SHORT',
    BotSignal.status == 'CLOSED'
).all()

results = [s.result for s in short_signals if s.result]
short_win_rate = sum(1 for r in results if r.is_win) / len(results) * 100
```

---

## 🚀 NEXT STEPS

1. ✅ Import CSV trade history
2. ✅ Bot gửi signals → lưu DB
3. ✅ Tracker monitor real-time
4. ✅ Đối soát performance
5. 📊 Build dashboard (optional)
6. 📈 Advanced analytics (optional)

---

**Database Location:** `signala.db` (SQLite)

**Backup:**
```bash
cp signala.db signala_backup_$(date +%Y%m%d).db
```
