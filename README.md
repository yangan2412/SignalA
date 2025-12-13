# SignalA - Telegram Trading Signal Bot

Bot phân tích lịch sử giao dịch BingX và tự động gửi tín hiệu Long/Short qua Telegram.

## Features

- Kết nối BingX API (read-only) để lấy trade history
- Phân tích patterns và win rate từ lịch sử giao dịch thực tế
- Xây dựng chiến lược dựa trên dữ liệu của bạn
- Gửi tín hiệu real-time qua Telegram
- Backtest và performance tracking
- Chạy trên Docker

## Quick Start

```bash
# Clone repository
git clone https://github.com/yangan2412/SignalA.git
cd SignalA

# Copy environment file
cp .env.example .env

# Edit .env với API keys của bạn
nano .env

# Chạy với Docker
docker-compose up -d
```

## API Key Setup

### BingX API (READ-ONLY)
1. Vào BingX → Account → API Management
2. Create API Key với:
   - ✅ Enable Reading
   - ❌ Disable Trading
   - ❌ Disable Withdrawals

### Telegram Bot
1. Tìm @BotFather trên Telegram
2. Gửi /newbot và làm theo hướng dẫn
3. Lưu Bot Token

## Project Status

🚧 Đang phát triển...

## Branches

- `main`: Production-ready code
- `dev`: Development branch
