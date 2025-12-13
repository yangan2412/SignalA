# SignalA - Telegram Trading Signal Bot

🤖 Bot thông minh phân tích lịch sử giao dịch BingX của bạn và tự động gửi tín hiệu Long/Short qua Telegram.

## ✨ Features

- 🔍 **Phân tích lịch sử giao dịch**: Học từ trades thực tế của bạn
- 📊 **Pattern Recognition**: Tìm win rate, best trading hours, symbol performance
- 🧠 **Learned Strategy**: Tự động xây dựng chiến lược dựa trên thành công của bạn
- 📈 **Technical Analysis**: RSI, MACD, EMA và nhiều indicators khác
- 💬 **Telegram Alerts**: Nhận tín hiệu real-time với entry, SL, TP
- 🐳 **Docker Ready**: Deploy dễ dàng với Docker
- 🔒 **Read-Only API**: An toàn tuyệt đối, không có quyền trade

## 📋 Yêu cầu

- Python 3.11+
- Docker & Docker Compose (khuyến nghị)
- BingX Account với API key (read-only)
- Telegram Bot Token

## 🚀 Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/yangan2412/SignalA.git
cd SignalA
```

### 2. Setup API Keys

#### BingX API (READ-ONLY)
⚠️ **QUAN TRỌNG**: Chỉ tạo API key với quyền READ-ONLY

1. Vào [BingX](https://bingx.com) → Account → API Management
2. Create New API Key với:
   - ✅ **Enable Reading** (Đọc dữ liệu)
   - ❌ **DISABLE Trading** (Tắt giao dịch)
   - ❌ **DISABLE Withdrawals** (Tắt rút tiền)
3. (Optional) Whitelist IP để tăng bảo mật
4. Lưu lại **API Key** và **Secret Key**

#### Telegram Bot Token

1. Mở Telegram và tìm [@BotFather](https://t.me/BotFather)
2. Gửi `/newbot` và làm theo hướng dẫn
3. Lưu lại **Bot Token** (format: `123456:ABC-DEF...`)
4. Lấy **Chat ID**:
   - Tìm [@userinfobot](https://t.me/userinfobot)
   - Gửi bất kỳ tin nhắn nào
   - Lưu lại **ID** (số bắt đầu bằng số)

### 3. Configure Environment

```bash
# Copy example config
cp .env.example .env

# Edit với editor yêu thích
nano .env
```

Điền thông tin vào `.env`:

```env
# BingX API
BINGX_API_KEY=your_api_key_here
BINGX_SECRET_KEY=your_secret_key_here

# Telegram Bot
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
TELEGRAM_CHAT_ID=your_chat_id

# Trading Config
TRADING_PAIRS=BTC-USDT,ETH-USDT
DEFAULT_TIMEFRAME=1h
SIGNAL_CONFIDENCE_THRESHOLD=0.7
```

### 4. Chạy Bot

#### Với Docker (Khuyến nghị)

```bash
# Build và start
docker-compose up -d

# Xem logs
docker-compose logs -f

# Stop bot
docker-compose down
```

#### Hoặc chạy trực tiếp với Python

```bash
# Cài dependencies
pip install -r requirements.txt

# Chạy bot
python main.py
```

## 📊 Bot sẽ làm gì?

1. **Kết nối BingX API** và verify credentials
2. **Lấy trade history** 30 ngày gần nhất
3. **Phân tích dữ liệu**:
   - Win rate tổng thể
   - Performance theo từng symbol
   - Best trading hours
   - Patterns (consecutive wins/losses, revenge trading)
4. **Gửi Analysis Report** qua Telegram
5. **Build Learned Strategy** dựa trên dữ liệu của bạn
6. **Monitor markets** và gửi tín hiệu khi phát hiện setup tốt

## 📱 Telegram Commands

- `/start` - Khởi động bot
- `/status` - Kiểm tra trạng thái bot
- `/help` - Xem hướng dẫn

## 📈 Signal Format

```
🟢 LONG SIGNAL - BTC-USDT

💰 Entry: $42,500.00
🛑 Stop Loss: $41,650.00 (2.00%)
🎯 Take Profit 1: $43,350.00 (+2.00%)
🎯 Take Profit 2: $44,200.00 (+4.00%)

📊 Indicators:
  • RSI: 32.5 (oversold)
  • MACD: Bullish crossover
  • Price: Above EMA 50

⚖️ Risk/Reward: 1:2.0
🎯 Confidence: ⭐⭐⭐⭐ (75%)
🤖 Strategy: Learned Strategy
```

## 🏗️ Project Structure

```
SignalA/
├── config/
│   ├── __init__.py
│   └── settings.py          # Configuration management
├── src/
│   ├── api/
│   │   ├── __init__.py
│   │   └── bingx_client.py  # BingX API wrapper
│   ├── analysis/
│   │   ├── __init__.py
│   │   └── trade_analyzer.py # Trade history analysis
│   ├── strategies/
│   │   ├── __init__.py
│   │   ├── base_strategy.py
│   │   └── learned_strategy.py # ML-based strategy
│   ├── bot/
│   │   ├── __init__.py
│   │   ├── telegram_bot.py   # Telegram integration
│   │   └── signal_manager.py # Signal cooldown management
│   └── utils/
│       ├── __init__.py
│       └── logger.py         # Logging utilities
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── main.py                   # Entry point
└── README.md
```

## 🔧 Configuration

### Trading Pairs
Edit `TRADING_PAIRS` trong `.env`:
```env
TRADING_PAIRS=BTC-USDT,ETH-USDT,SOL-USDT
```

### Timeframe
Các timeframe hỗ trợ: `1m`, `5m`, `15m`, `30m`, `1h`, `4h`, `1d`
```env
DEFAULT_TIMEFRAME=1h
```

### Signal Confidence
Điều chỉnh ngưỡng confidence (0.0 - 1.0):
```env
SIGNAL_CONFIDENCE_THRESHOLD=0.7
```

## 🛡️ Bảo mật

- ✅ API key chỉ có quyền READ-ONLY
- ✅ Không lưu API keys trong code
- ✅ Sử dụng environment variables
- ✅ `.env` file được gitignore
- ✅ Chạy trong Docker container isolated

## 📝 Logs

Logs được lưu trong `logs/bot.log`:
```bash
# Xem logs real-time
tail -f logs/bot.log

# Với Docker
docker-compose logs -f
```

## 🤝 Contributing

1. Fork repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📜 License

MIT License - xem file LICENSE

## ⚠️ Disclaimer

Bot này chỉ dùng cho mục đích giáo dục và tham khảo. Giao dịch cryptocurrency có rủi ro cao. Luôn DYOR (Do Your Own Research) và không bao giờ đầu tư số tiền bạn không thể mất.

## 🐛 Issues

Phát hiện bug hoặc có feature request? [Tạo issue mới](https://github.com/yangan2412/SignalA/issues)

## 📧 Contact

- GitHub: [@yangan2412](https://github.com/yangan2412)
- Project: [SignalA](https://github.com/yangan2412/SignalA)

---

Made with ❤️ by yangan2412 | Powered by Claude Code
