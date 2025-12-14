#!/usr/bin/env python3
"""
Migration script to add martingale support
- Creates position_sequences table
- Adds martingale-related columns to bot_signals table
"""

import sys
import os
from pathlib import Path

# Add parent directory to path to import models
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, inspect, text
from src.database.models import Base, PositionSequence, BotSignal
from config.settings import Settings


def check_table_exists(engine, table_name):
    """Check if a table exists in the database"""
    inspector = inspect(engine)
    return table_name in inspector.get_table_names()


def check_column_exists(engine, table_name, column_name):
    """Check if a column exists in a table"""
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def migrate():
    """Run the migration"""
    settings = Settings()
    database_url = settings.DATABASE_URL

    print(f"🔧 Starting migration for: {database_url}")
    print("=" * 60)

    # Create engine
    engine = create_engine(database_url)

    # Check if this is a fresh database (no tables)
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    if not existing_tables:
        print("📊 Fresh database detected - creating all tables...")
        Base.metadata.create_all(engine)
        print("✅ All tables created successfully!")
        return

    # Existing database - perform migration
    print("📊 Existing database detected - migrating...")
    print()

    # Step 1: Create position_sequences table if it doesn't exist
    if not check_table_exists(engine, 'position_sequences'):
        print("1️⃣  Creating position_sequences table...")
        PositionSequence.__table__.create(engine)
        print("   ✅ position_sequences table created")
    else:
        print("1️⃣  position_sequences table already exists - skipping")

    print()

    # Step 2: Add new columns to bot_signals table
    if check_table_exists(engine, 'bot_signals'):
        print("2️⃣  Updating bot_signals table...")

        columns_to_add = [
            ('signal_type', "VARCHAR(20) DEFAULT 'STANDALONE'"),
            ('sequence_id', "INTEGER"),
            ('step_number', "INTEGER DEFAULT 1"),
            ('actual_margin', "FLOAT"),
        ]

        with engine.connect() as conn:
            for col_name, col_definition in columns_to_add:
                if not check_column_exists(engine, 'bot_signals', col_name):
                    try:
                        # SQLite syntax
                        sql = f"ALTER TABLE bot_signals ADD COLUMN {col_name} {col_definition}"
                        conn.execute(text(sql))
                        conn.commit()
                        print(f"   ✅ Added column: {col_name}")
                    except Exception as e:
                        print(f"   ⚠️  Error adding {col_name}: {e}")
                else:
                    print(f"   ℹ️  Column {col_name} already exists - skipping")

        print()

    # Step 3: Update existing bot_signals to have default signal_type
    print("3️⃣  Setting default values for existing records...")
    with engine.connect() as conn:
        try:
            # Set all existing signals to STANDALONE type if they're NULL
            conn.execute(text("""
                UPDATE bot_signals
                SET signal_type = 'STANDALONE'
                WHERE signal_type IS NULL
            """))
            conn.commit()
            print("   ✅ Updated existing signals to STANDALONE type")
        except Exception as e:
            print(f"   ⚠️  Error updating records: {e}")

    print()
    print("=" * 60)
    print("🎉 Migration completed successfully!")
    print()
    print("Summary:")
    print(f"  • Database: {database_url}")
    print(f"  • Tables: {len(inspector.get_table_names())} total")
    print(f"  • New table: position_sequences")
    print(f"  • Updated table: bot_signals (4 new columns)")
    print()
    print("Next steps:")
    print("  1. Test imports: python test_imports.py")
    print("  2. Run bot: python main.py")


def rollback():
    """Rollback migration (if needed)"""
    settings = Settings()
    database_url = settings.DATABASE_URL

    print(f"⚠️  Rolling back migration for: {database_url}")
    print("=" * 60)

    engine = create_engine(database_url)

    # Drop position_sequences table
    if check_table_exists(engine, 'position_sequences'):
        print("Dropping position_sequences table...")
        PositionSequence.__table__.drop(engine)
        print("✅ Table dropped")

    # Cannot easily drop columns in SQLite, would need to recreate table
    print()
    print("⚠️  Note: SQLite doesn't support DROP COLUMN easily.")
    print("   New columns in bot_signals will remain but can be ignored.")
    print()
    print("✅ Rollback completed")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Migrate database for martingale support')
    parser.add_argument('--rollback', action='store_true', help='Rollback migration')
    args = parser.parse_args()

    if args.rollback:
        confirm = input("Are you sure you want to rollback? (yes/no): ")
        if confirm.lower() == 'yes':
            rollback()
        else:
            print("Rollback cancelled")
    else:
        migrate()
