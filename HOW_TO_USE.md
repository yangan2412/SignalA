# 🚀 HƯỚNG DẪN SỬ DỤNG SIGNALA BOT

## ✅ Đã Triển Khai Xong

Bot tín hiệu SHORT đã được xây dựng hoàn chỉnh dựa trên phân tích 95 trades với **81.1% win rate**.

---

## 📋 Các Files Đã Tạo/Sửa

### Files Mới:
1. **`src/api/symbol_selector.py`** - Chọn cặp để scan (2 modes)
2. **`src/strategies/data_driven_short_strategy.py`** - Strategy SHORT dựa trên data
3. **`test_imports.py`** - Script test imports

### Files Đã Sửa:
1. **`src/api/bingx_client.py`** - Thêm `get_24hr_tickers()`
2. **`src/database/db_manager.py`** - Thêm `get_signal_by_id()`
3. **`src/database/signal_tracker.py`** - Thêm Telegram notifications
4. **`main.py`** - Integrate tất cả components
5. **`config/settings.py`** - Thêm SYMBOL_MODE configs
6. **`.env`** - Thêm SYMBOL_MODE, VOLATILITY_TOP_N, VOLATILITY_MIN_VOLUME

---

## 🔧 SETUP & CONFIGURATION

### 1. **Cấu Hình Telegram Bot**

Mở file `.env` và điền thông tin Telegram bot:

```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_telegram_chat_id_here
```

**Cách lấy Telegram Bot Token:**
1. Chat với @BotFather trên Telegram
2. Gửi `/newbot` và làm theo hướng dẫn
3. Copy token được cung cấp

**Cách lấy Chat ID:**
1. Chat với bot của bạn
2. Truy cập: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
3. Tìm `"chat":{"id":123456789}` và copy số đó

### 2. **Chọn Chế Độ Scan Cặp**

Trong file `.env`:

**Option 1: Whitelist Mode (Recommended)**
```env
SYMBOL_MODE=whitelist
```
- Scan 7 cặp đã được phân tích: turbo, cake, the, portal, 1000bonk, xrp, btc
- Đã có dữ liệu lịch sử win rate cao
- An toàn và ổn định

**Option 2: Volatility Mode**
```env
SYMBOL_MODE=volatility
VOLATILITY_TOP_N=20
VOLATILITY_MIN_VOLUME=1000000
```
- Tự động scan top 20 cặp biến động lớn nhất 24h
- Nhiều cơ hội hơn
- Volume tối thiểu 1M USDT

---

## 🚀 CHẠY BOT

### 1. **Kiểm Tra Imports**
```bash
python3 test_imports.py
```

Nếu thấy "✅ ALL TESTS PASSED!" thì OK.

### 2. **Chạy Bot**
```bash
python3 main.py
```

Bot sẽ:
1. Kết nối BingX API
2. Khởi tạo database
3. Khởi động Telegram bot
4. Bắt đầu scan thị trường mỗi 5 phút
5. Gửi tín hiệu SHORT khi phát hiện cơ hội

---

## 📊 CÁCH BOT HOẠT ĐỘNG

### Main Loop (Mỗi 5 phút):
```
1. Lấy danh sách symbols (whitelist hoặc volatility)
2. Với mỗi symbol:
   - Lấy 200 nến 4h
   - Tính RSI, MACD, EMA50
   - Kiểm tra điều kiện SHORT:
     ✓ RSI > 65 (overbought)
     ✓ MACD bearish crossunder
     ✓ Price < EMA50
   - Tính confidence score
   - Nếu confidence >= 0.7:
     → Lưu signal vào DB
     → Gửi Telegram notification
3. Chờ 5 phút, lặp lại
```

### Signal Tracker (Mỗi 60 giây):
```
1. Lấy tất cả active signals từ DB
2. Với mỗi signal:
   - Get current price
   - Check có hit TP1/TP2/SL không
   - Nếu hit:
     → Update DB (status = CLOSED)
     → Gửi Telegram notification với kết quả
```

---

## 📱 TELEGRAM NOTIFICATIONS

### 1. **New Signal Message:**
```
🔴 SHORT SIGNAL - TURBO-USDT

💰 Entry: $0.006495
🛑 Stop Loss: $0.006820 (+5.00%)
🎯 Take Profit 1: $0.005975 (-8.00%)
🎯 Take Profit 2: $0.005651 (-13.00%)

📊 Indicators:
  • RSI: 72.5 (overbought)
  • MACD: Bearish crossunder
  • Price: Below EMA 50

⚖️ Risk/Reward: 1:2.6
🎯 Confidence: ⭐⭐⭐⭐ (85%)
💼 Leverage: 25x | Margin: $20

🤖 Strategy: Data-Driven SHORT Strategy
🕐 2025-12-13 14:30:00 UTC
```

### 2. **Signal Closed Message:**
```
🎯🎯 SIGNAL CLOSED - TURBO-USDT

📊 Result: HIT_TP2
💰 Entry: $0.006495
💰 Exit: $0.005651
📈 PnL: $+277.60 (+46.30%)

⏱ Duration: 833.9 hours
🤖 Strategy: Data-Driven SHORT Strategy
```

---

## 🎯 LEVERAGE & MARGIN

Bot tự động điều chỉnh dựa trên confidence:

| Confidence | Leverage | Margin | Notes |
|-----------|----------|--------|-------|
| 85%+ | 25x | $20 | High confidence - Best symbols |
| 70-85% | 20x | $15 | Medium confidence |
| <70% | - | - | Không gửi signal |

**Symbols có confidence boost:**
- THE-USDT: +15% (100% win rate lịch sử)
- PORTAL-USDT: +15% (100% win rate)
- TURBO-USDT: +10% (85.7% win rate)
- CAKE-USDT: +5% (75% win rate)

---

## 📊 DATABASE TRACKING

Tất cả signals được lưu vào `signala.db`:

**Xem signals đã gửi:**
```bash
sqlite3 signala.db "SELECT * FROM bot_signals ORDER BY signal_time DESC LIMIT 10;"
```

**Xem kết quả signals:**
```bash
sqlite3 signala.db "SELECT * FROM signal_results ORDER BY exit_time DESC LIMIT 10;"
```

**Xem performance:**
```bash
python3 -c "
from src.database.db_manager import DatabaseManager
db = DatabaseManager('sqlite:///signala.db')
perf = db.get_bot_performance(days=30)
print(f'Win Rate: {perf[\"win_rate\"]}%')
print(f'Total PNL: ${perf[\"total_pnl\"]}')
"
```

---

## 🔧 TROUBLESHOOTING

### Bot không kết nối được BingX:
```bash
# Kiểm tra API keys
python3 -c "from config.settings import Settings; Settings().validate()"
```

### Bot không gửi Telegram:
- Kiểm tra TELEGRAM_BOT_TOKEN và TELEGRAM_CHAT_ID
- Test bot với @userinfobot để lấy chat ID chính xác

### Không có signals:
- Bình thường! Bot chỉ gửi khi có HIGH-PROBABILITY setup
- RSI phải > 65, MACD bearish, price < EMA50
- Confidence phải >= 70%
- Có thể chờ vài giờ/ngày mới có signal

### Database errors:
```bash
# Reset database
rm signala.db
# Bot sẽ tự tạo lại khi chạy
```

---

## 📈 EXPECTED PERFORMANCE

Dựa trên 95 trades lịch sử:

**Conservative (70% win rate):**
- 30 trades/month → ~$990 profit/month

**Realistic (81% win rate):**
- 30 trades/month → ~$1,287 profit/month

**Risk:**
- Max 3 consecutive losses lịch sử
- Max drawdown: ~$134

---

## ⚙️ ADVANCED CONFIGURATION

### Thay đổi timeframe:
Sửa trong `main.py` line 138:
```python
interval='4h'  # Có thể đổi thành '1h', '2h', '6h', '12h', '1d'
```

### Thay đổi scan interval:
Sửa trong `main.py` line 195:
```python
await asyncio.sleep(300)  # 300s = 5 phút
```

### Thay đổi TP/SL levels:
Sửa trong `src/strategies/data_driven_short_strategy.py`:
```python
self.tp1_percent = 8   # -8% from entry
self.tp2_percent = 13  # -13% from entry
self.sl_percent = 5    # +5% from entry
```

---

## 📚 FILES STRUCTURE

```
SignalA/
├── main.py                    # Main entry point
├── config/
│   └── settings.py           # Configuration
├── src/
│   ├── api/
│   │   ├── bingx_client.py   # BingX API wrapper
│   │   └── symbol_selector.py # Symbol selection (whitelist/volatility)
│   ├── strategies/
│   │   ├── base_strategy.py
│   │   └── data_driven_short_strategy.py  # SHORT strategy
│   ├── database/
│   │   ├── models.py          # SQLAlchemy models
│   │   ├── db_manager.py      # Database operations
│   │   └── signal_tracker.py  # Signal monitoring
│   └── bot/
│       ├── telegram_bot.py    # Telegram integration
│       └── signal_manager.py  # Cooldown management
├── signala.db                 # Database (auto-created)
└── logs/
    └── bot.log               # Logs
```

---

## 🎓 TIPS

1. **Bắt đầu với whitelist mode** để test bot ổn định
2. **Kiểm tra logs** thường xuyên: `tail -f logs/bot.log`
3. **Không trade mọi signal** - chỉ chọn confidence cao nhất
4. **Theo dõi results** trong database để đánh giá
5. **Backup database** định kỳ: `cp signala.db signala_backup.db`

---

## 🚨 IMPORTANT NOTES

⚠️ **Đây là BOT TÍN HIỆU - KHÔNG TỰ ĐỘNG TRADE**

- Bot chỉ GỬI TÍN HIỆU qua Telegram
- Bạn phải TỰ VÀO LỆNH trên BingX
- Bot KHÔNG có quyền trade trên account của bạn
- Theoretical PnL chỉ là ƯỚC TÍNH dựa trên margin/leverage recommended

⚠️ **RISK DISCLAIMER**

- Trading có rủi ro cao
- Không đầu tư quá khả năng chịu đựng
- Luôn sử dụng Stop Loss
- Past performance không đảm bảo tương lai

---

## 📞 SUPPORT

Nếu gặp vấn đề:
1. Kiểm tra logs: `tail -f logs/bot.log`
2. Chạy test: `python3 test_imports.py`
3. Kiểm tra .env configuration
4. Xem plan file: `/root/.claude/plans/hazy-prancing-cocoa.md`

---

**Chúc bạn trade thành công! 🚀**
