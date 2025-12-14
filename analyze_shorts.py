#!/usr/bin/env python3
"""
Script để phân tích các lệnh SHORT từ BingX account
"""

import sys
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from config import settings
from src.api.bingx_client import BingXClient
from src.analysis.trade_analyzer import TradeAnalyzer

def main():
    print("=" * 70)
    print("  PHÂN TÍCH LỆNH SHORT - BingX Trading Analysis")
    print("=" * 70)
    print()

    # Initialize BingX client
    print("🔗 Đang kết nối BingX API...")
    client = BingXClient(
        api_key=settings.BINGX_API_KEY,
        secret_key=settings.BINGX_SECRET_KEY,
        base_url=settings.BINGX_BASE_URL
    )

    # Test connection
    if not client.test_connection():
        print("❌ Không thể kết nối BingX API. Vui lòng kiểm tra API keys.")
        return

    print("✅ Kết nối thành công!\n")

    # Get account info
    print("📊 Thông tin tài khoản:")
    try:
        account_info = client.get_account_info()
        print(f"   Account: {account_info.get('data', {})}")
        print()
    except Exception as e:
        print(f"   Không lấy được thông tin account: {e}\n")

    # Fetch trade history (90 days)
    print("📥 Đang lấy lịch sử giao dịch 90 ngày gần nhất...")
    end_time = int(datetime.now().timestamp() * 1000)
    start_time = int((datetime.now() - timedelta(days=90)).timestamp() * 1000)

    all_trades = []
    symbols = ['BTC-USDT', 'ETH-USDT', 'SOL-USDT', 'BNB-USDT', 'XRP-USDT']

    for symbol in symbols:
        try:
            trades = client.get_trade_history(
                symbol=symbol,
                start_time=start_time,
                end_time=end_time,
                limit=500
            )
            if trades:
                print(f"   ✓ {symbol}: {len(trades)} trades")
                all_trades.extend(trades)
        except Exception as e:
            print(f"   ✗ {symbol}: {e}")

    if not all_trades:
        print("\n❌ Không tìm thấy lịch sử giao dịch nào!")
        print("💡 Tips:")
        print("   - Kiểm tra API key có quyền đọc trade history không")
        print("   - Thử thay đổi symbols hoặc timeframe")
        return

    print(f"\n✅ Tổng cộng: {len(all_trades)} trades\n")

    # Filter SHORT trades only
    df = pd.DataFrame(all_trades)
    print("🔍 Lọc các lệnh SHORT...")

    # Analyze based on 'side' or 'positionSide'
    if 'side' in df.columns:
        short_trades = df[df['side'] == 'SELL'].to_dict('records')
    elif 'positionSide' in df.columns:
        short_trades = df[df['positionSide'] == 'SHORT'].to_dict('records')
    else:
        print("⚠️ Không tìm thấy column 'side' hoặc 'positionSide'")
        print("📋 Columns có sẵn:", df.columns.tolist())
        short_trades = []

    if not short_trades:
        print(f"\n⚠️ Không tìm thấy lệnh SHORT nào trong {len(all_trades)} trades")
        print("\n📊 Phân tích tất cả trades thay thế:\n")
        short_trades = all_trades
    else:
        print(f"✅ Tìm thấy {len(short_trades)} lệnh SHORT\n")

    # Analyze SHORT trades
    print("=" * 70)
    print("  📊 PHÂN TÍCH CHI TIẾT")
    print("=" * 70)

    analyzer = TradeAnalyzer(short_trades)

    # Print general statistics
    print("\n" + analyzer.generate_report())

    # Detailed SHORT analysis
    print("\n" + "=" * 70)
    print("  🎯 PHÂN TÍCH ĐIỂM VÀO LỆNH SHORT")
    print("=" * 70)

    analyze_short_entry_patterns(short_trades)

    print("\n" + "=" * 70)
    print("  💰 PHÂN TÍCH ĐIỂM CHỐT LỜI")
    print("=" * 70)

    analyze_short_exit_patterns(short_trades)

    # Symbol-specific analysis
    symbol_perf = analyzer.get_symbol_performance()
    if not symbol_perf.empty:
        print("\n" + "=" * 70)
        print("  📈 PERFORMANCE THEO SYMBOL")
        print("=" * 70)
        print(symbol_perf.to_string())

    # Time-based analysis
    time_analysis = analyzer.get_time_based_analysis()
    if time_analysis:
        print("\n" + "=" * 70)
        print("  ⏰ PHÂN TÍCH THEO THỜI GIAN")
        print("=" * 70)

        best_hours = time_analysis.get('best_trading_hours', [])
        worst_hours = time_analysis.get('worst_trading_hours', [])

        print(f"\n✅ Khung giờ tốt nhất: {', '.join([f'{h}:00' for h in best_hours])}")
        print(f"❌ Khung giờ tệ nhất: {', '.join([f'{h}:00' for h in worst_hours])}")

    print("\n" + "=" * 70)
    print("  ✨ HOÀN TẤT PHÂN TÍCH")
    print("=" * 70)

def analyze_short_entry_patterns(trades):
    """Phân tích patterns điểm vào lệnh SHORT"""

    if not trades:
        print("\nKhông có dữ liệu để phân tích.")
        return

    df = pd.DataFrame(trades)

    # Convert to numeric
    for col in ['price', 'avgPrice', 'profit', 'origQty']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # Filter profitable shorts
    if 'profit' in df.columns:
        profitable = df[df['profit'] > 0]
        losing = df[df['profit'] < 0]

        print(f"\n✅ Lệnh SHORT thắng: {len(profitable)}")
        print(f"❌ Lệnh SHORT thua: {len(losing)}")

        if len(profitable) > 0:
            print("\n💡 ĐẶC ĐIỂM LỆNH SHORT THÀNH CÔNG:")
            print(f"   • Giá vào trung bình: ${profitable['avgPrice'].mean():.2f}")
            print(f"   • Profit trung bình: ${profitable['profit'].mean():.2f}")
            print(f"   • Max profit: ${profitable['profit'].max():.2f}")

            # Analyze time patterns for profitable shorts
            if 'time' in df.columns:
                profitable['hour'] = pd.to_datetime(profitable['time'], unit='ms').dt.hour
                best_hours = profitable.groupby('hour').size().sort_values(ascending=False).head(3)
                print(f"\n   ⏰ Giờ vào lệnh hay thắng nhất:")
                for hour, count in best_hours.items():
                    print(f"      • {hour}:00 - {count} lệnh thắng")

        if len(losing) > 0:
            print("\n⚠️ ĐẶC ĐIỂM LỆNH SHORT THẤT BẠI:")
            print(f"   • Giá vào trung bình: ${losing['avgPrice'].mean():.2f}")
            print(f"   • Loss trung bình: ${abs(losing['profit'].mean()):.2f}")
            print(f"   • Max loss: ${abs(losing['profit'].min()):.2f}")

    # Position size analysis
    if 'origQty' in df.columns:
        print("\n📊 PHÂN TÍCH POSITION SIZE:")
        print(f"   • Position size trung bình: {df['origQty'].mean():.4f}")
        print(f"   • Position size lớn nhất: {df['origQty'].max():.4f}")
        print(f"   • Position size nhỏ nhất: {df['origQty'].min():.4f}")

def analyze_short_exit_patterns(trades):
    """Phân tích patterns điểm chốt lời"""

    if not trades:
        print("\nKhông có dữ liệu để phân tích.")
        return

    df = pd.DataFrame(trades)

    # Convert to numeric
    for col in ['price', 'avgPrice', 'profit', 'executedQty', 'takeProfit', 'stopLoss']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    if 'profit' in df.columns and 'avgPrice' in df.columns:
        profitable = df[df['profit'] > 0].copy()

        if len(profitable) > 0:
            # Calculate profit percentage
            profitable['profit_pct'] = (profitable['profit'] / (profitable['avgPrice'] * profitable.get('executedQty', 1))) * 100

            print(f"\n💰 PHÂN TÍCH CHỐT LỜI:")
            print(f"   • Profit % trung bình: {profitable['profit_pct'].mean():.2f}%")
            print(f"   • Profit % cao nhất: {profitable['profit_pct'].max():.2f}%")
            print(f"   • Profit % thấp nhất: {profitable['profit_pct'].min():.2f}%")

            # Categorize by profit level
            small_profits = profitable[profitable['profit_pct'] < 2]
            medium_profits = profitable[(profitable['profit_pct'] >= 2) & (profitable['profit_pct'] < 5)]
            large_profits = profitable[profitable['profit_pct'] >= 5]

            print(f"\n📈 PHÂN BỐ PROFIT:")
            print(f"   • Profit nhỏ (<2%): {len(small_profits)} lệnh")
            print(f"   • Profit trung bình (2-5%): {len(medium_profits)} lệnh")
            print(f"   • Profit lớn (>5%): {len(large_profits)} lệnh")

    # Analyze TP/SL usage
    if 'takeProfit' in df.columns and 'stopLoss' in df.columns:
        has_tp = df[df['takeProfit'].notna()]
        has_sl = df[df['stopLoss'].notna()]

        print(f"\n🎯 SỬ DỤNG TP/SL:")
        print(f"   • Lệnh có set Take Profit: {len(has_tp)}/{len(df)}")
        print(f"   • Lệnh có set Stop Loss: {len(has_sl)}/{len(df)}")

        if len(has_tp) > 0 and 'avgPrice' in df.columns:
            has_tp['tp_distance_pct'] = abs((has_tp['takeProfit'] - has_tp['avgPrice']) / has_tp['avgPrice'] * 100)
            print(f"   • TP distance trung bình: {has_tp['tp_distance_pct'].mean():.2f}%")

        if len(has_sl) > 0 and 'avgPrice' in df.columns:
            has_sl['sl_distance_pct'] = abs((has_sl['stopLoss'] - has_sl['avgPrice']) / has_sl['avgPrice'] * 100)
            print(f"   • SL distance trung bình: {has_sl['sl_distance_pct'].mean():.2f}%")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Đã dừng phân tích.")
    except Exception as e:
        print(f"\n❌ Lỗi: {e}")
        import traceback
        traceback.print_exc()
