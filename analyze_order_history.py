#!/usr/bin/env python3
"""
Analyze order history from Excel file
"""

import pandas as pd

df = pd.read_excel('Order_His.csv')

print('='*80)
print('TRADE HISTORY SUMMARY')
print('='*80)
print(f'\nTotal trades: {len(df)}')
print(f'\nDirection breakdown:')
print(df['direction'].value_counts())
print(f'\nCategory breakdown:')
print(df['category'].value_counts())
print(f'\nMargin Type breakdown:')
print(df['marginType'].value_counts())

# Filter SHORT trades
shorts = df[df['direction'] == 'short']
print(f'\n\n{'='*80}')
print(f'SHORT TRADES ANALYSIS ({len(shorts)} trades)')
print('='*80)

# Win/Loss analysis
shorts_win = shorts[shorts['Realized PNL'] > 0]
shorts_loss = shorts[shorts['Realized PNL'] <= 0]

print(f'\nWinning trades: {len(shorts_win)} ({len(shorts_win)/len(shorts)*100:.1f}%)')
print(f'Losing trades: {len(shorts_loss)} ({len(shorts_loss)/len(shorts)*100:.1f}%)')
print(f'\nTotal PNL: ${shorts["Realized PNL"].sum():.2f}')
print(f'Average PNL per trade: ${shorts["Realized PNL"].mean():.2f}')
print(f'Best trade: ${shorts["Realized PNL"].max():.2f}')
print(f'Worst trade: ${shorts["Realized PNL"].min():.2f}')

print(f'\n\nLeverage used:')
print(shorts['leverage'].value_counts().sort_index())

print(f'\n\nMargin used:')
print(shorts['margin'].value_counts().sort_index())

print(f'\n\nSymbols traded (SHORT):')
print(shorts['category'].value_counts())

print(f'\n\nSample SHORT trades:')
print(shorts[['Order No', 'category', 'margin', 'leverage', 'openPrice', 'closePrice', 'Realized PNL']].head(10).to_string())

# Time analysis
df['openTime'] = pd.to_datetime(df['openTime(UTC+8)'])
df['closeTime'] = pd.to_datetime(df['closeTime(UTC+8)'])
shorts = df[df['direction'] == 'short'].copy()
shorts['duration_hours'] = (shorts['closeTime'] - shorts['openTime']).dt.total_seconds() / 3600

print(f'\n\nDuration analysis:')
print(f'Average trade duration: {shorts["duration_hours"].mean():.1f} hours')
print(f'Median trade duration: {shorts["duration_hours"].median():.1f} hours')
print(f'Shortest trade: {shorts["duration_hours"].min():.1f} hours')
print(f'Longest trade: {shorts["duration_hours"].max():.1f} hours')
