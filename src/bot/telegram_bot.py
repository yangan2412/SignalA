import asyncio
import logging
from typing import Dict, Optional
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from datetime import datetime

logger = logging.getLogger(__name__)

class TradingSignalBot:
    """Telegram bot để gửi trading signals"""

    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.app = None
        self.is_running = False

    async def initialize(self):
        """Initialize bot application"""
        self.app = Application.builder().token(self.bot_token).build()

        # Add command handlers
        self.app.add_handler(CommandHandler("start", self.cmd_start))
        self.app.add_handler(CommandHandler("status", self.cmd_status))
        self.app.add_handler(CommandHandler("help", self.cmd_help))

        logger.info("Telegram bot initialized")

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for /start command"""
        welcome_msg = """
🤖 <b>SignalA Trading Bot Started!</b>

Bot đang hoạt động và sẽ gửi tín hiệu giao dịch khi phát hiện setup phù hợp.

Commands:
/status - Kiểm tra trạng thái bot
/help - Xem hướng dẫn
        """
        await update.message.reply_text(welcome_msg, parse_mode='HTML')

    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for /status command"""
        status_msg = f"""
📊 <b>Bot Status</b>

✅ Running
⏰ Server Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🔄 Monitoring markets...
        """
        await update.message.reply_text(status_msg, parse_mode='HTML')

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for /help command"""
        help_msg = """
📚 <b>Help Guide</b>

Bot tự động phân tích thị trường và gửi tín hiệu dựa trên:
• Lịch sử giao dịch của bạn
• Technical indicators (RSI, MACD, EMA)
• Best trading hours từ analysis

<b>Signal Format:</b>
🟢/🔴 Direction
💰 Entry Price
🛑 Stop Loss
🎯 Take Profit levels
📊 Indicators
⭐ Confidence score

<b>Commands:</b>
/start - Khởi động bot
/status - Xem trạng thái
/help - Xem hướng dẫn này
        """
        await update.message.reply_text(help_msg, parse_mode='HTML')

    async def send_signal(self, signal: Dict):
        """
        Send trading signal to Telegram

        Args:
            signal: Signal dictionary from strategy
        """
        try:
            message = self._format_signal_message(signal)

            # Send to specified chat
            await self.app.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='HTML'
            )

            logger.info(f"Signal sent: {signal['side']} {signal['symbol']}")

        except Exception as e:
            logger.error(f"Failed to send signal: {e}")

    def _format_signal_message(self, signal: Dict) -> str:
        """Format signal into readable Telegram message"""
        side = signal['side']
        emoji = "🟢" if side == "LONG" else "🔴"
        direction = "LONG" if side == "LONG" else "SHORT"

        # Calculate percentages
        entry = signal['entry_price']
        sl = signal['stop_loss']
        tp1 = signal['take_profit_1']
        tp2 = signal['take_profit_2']

        sl_pct = abs((sl - entry) / entry * 100)
        tp1_pct = abs((tp1 - entry) / entry * 100)
        tp2_pct = abs((tp2 - entry) / entry * 100)

        # Calculate R:R
        risk_reward = tp2_pct / sl_pct if sl_pct > 0 else 0

        # Format indicators
        indicators_text = "\n".join([
            f"  • {key}: {value}"
            for key, value in signal.get('indicators', {}).items()
        ])

        # Confidence stars
        confidence = signal.get('confidence', 0.5)
        stars = "⭐" * int(confidence * 5)

        message = f"""
{emoji} <b>{direction} SIGNAL - {signal['symbol']}</b>

💰 <b>Entry:</b> ${entry:,.2f}
🛑 <b>Stop Loss:</b> ${sl:,.2f} ({sl_pct:.2f}%)
🎯 <b>Take Profit 1:</b> ${tp1:,.2f} (+{tp1_pct:.2f}%)
🎯 <b>Take Profit 2:</b> ${tp2:,.2f} (+{tp2_pct:.2f}%)

📊 <b>Indicators:</b>
{indicators_text}

⚖️ <b>Risk/Reward:</b> 1:{risk_reward:.1f}
🎯 <b>Confidence:</b> {stars} ({confidence*100:.0f}%)
🤖 <b>Strategy:</b> {signal.get('strategy', 'Unknown')}

<i>⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>
        """

        return message.strip()

    async def send_analysis_report(self, report: str):
        """Send trade analysis report"""
        try:
            # Split long report into chunks if needed
            max_length = 4000
            if len(report) > max_length:
                chunks = [report[i:i+max_length] for i in range(0, len(report), max_length)]
                for chunk in chunks:
                    await self.app.bot.send_message(
                        chat_id=self.chat_id,
                        text=f"<pre>{chunk}</pre>",
                        parse_mode='HTML'
                    )
                    await asyncio.sleep(1)
            else:
                await self.app.bot.send_message(
                    chat_id=self.chat_id,
                    text=f"<pre>{report}</pre>",
                    parse_mode='HTML'
                )

            logger.info("Analysis report sent")

        except Exception as e:
            logger.error(f"Failed to send report: {e}")

    async def start(self):
        """Start the bot"""
        await self.app.initialize()
        await self.app.start()
        self.is_running = True
        logger.info("Telegram bot started")

    async def stop(self):
        """Stop the bot"""
        if self.app:
            await self.app.stop()
            await self.app.shutdown()
        self.is_running = False
        logger.info("Telegram bot stopped")
