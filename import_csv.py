#!/usr/bin/env python3
"""
Import CSV trade history vào database
"""

import sys
from src.database.db_manager import DatabaseManager

def main():
    if len(sys.argv) < 2:
        print("Usage: python import_csv.py <csv_file_path>")
        print("\nExample:")
        print("  python import_csv.py trades_history.csv")
        sys.exit(1)

    csv_file = sys.argv[1]

    print("=" * 80)
    print("  📥 IMPORT TRADE HISTORY FROM CSV")
    print("=" * 80)
    print()

    # Initialize database
    print("🗄️  Initializing database...")
    db = DatabaseManager('sqlite:///signala.db')
    print("✅ Database initialized")
    print()

    # Import CSV
    print(f"📂 Reading CSV file: {csv_file}")
    try:
        result = db.import_user_trades_from_csv(csv_file)

        print()
        print("=" * 80)
        print("  ✅ IMPORT COMPLETED")
        print("=" * 80)
        print()
        print(f"📊 Results:")
        print(f"   • Total records in CSV: {result['total']}")
        print(f"   • Imported: {result['imported']}")
        print(f"   • Skipped (duplicates): {result['skipped']}")
        print()

        # Show sample
        if result['imported'] > 0:
            print("📋 Sample imported trades:")
            trades = db.get_user_trades(limit=5)
            for trade in trades[:5]:
                print(f"   • {trade.symbol} {trade.position_side} @ ${trade.entry_price:.5f} "
                      f"→ ${trade.close_price:.5f} = ${trade.profit:+.2f}")
            print()

        print("✅ Ready to analyze!")
        print()
        print("Next steps:")
        print("  1. python analyze_trades.py        # Phân tích trades")
        print("  2. python main.py                  # Chạy bot")
        print()

    except FileNotFoundError:
        print(f"❌ Error: File not found: {csv_file}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error during import: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
