#!/usr/bin/env python3
"""
Test tất cả endpoints có thể để tìm trade history
"""

import hmac
import hashlib
import time
import requests
import json

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

def test_endpoint(endpoint, params=None, description=""):
    print(f"\n{'='*80}")
    print(f"Testing: {description}")
    print(f"Endpoint: {endpoint}")
    print(f"{'='*80}")

    if params is None:
        params = {}

    params['timestamp'] = int(time.time() * 1000)
    signature = generate_signature(params, SECRET_KEY)
    params['signature'] = signature

    headers = {'X-BX-APIKEY': API_KEY}

    url = f"{BASE_URL}{endpoint}"
    response = requests.get(url, params=params, headers=headers)

    print(f"Status: {response.status_code}")

    try:
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")

        # Check if has data
        if data.get('code') == 0:
            if 'data' in data and data['data']:
                print(f"✅ HAS DATA!")
                return True
        else:
            print(f"❌ Error: {data.get('msg')}")
    except:
        print(f"Raw response: {response.text}")

    return False

print("\n" + "="*80)
print("  🔍 KIỂM TRA TẤT CẢ ENDPOINTS ĐỂ TÌM TRADE HISTORY")
print("="*80)

# Test 1: Current positions
test_endpoint(
    "/openApi/swap/v2/user/positions",
    {},
    "Current Positions (Perpetual)"
)

# Test 2: Open orders
test_endpoint(
    "/openApi/swap/v2/trade/openOrders",
    {},
    "Open Orders (Perpetual)"
)

# Test 3: All orders (no symbol)
test_endpoint(
    "/openApi/swap/v2/trade/allOrders",
    {},
    "All Orders - No Symbol (Perpetual)"
)

# Test 4: All orders BTC-USDT
test_endpoint(
    "/openApi/swap/v2/trade/allOrders",
    {'symbol': 'BTC-USDT'},
    "All Orders - BTC-USDT (Perpetual)"
)

# Test 5: All orders BTCUSDT (no dash)
test_endpoint(
    "/openApi/swap/v2/trade/allOrders",
    {'symbol': 'BTCUSDT'},
    "All Orders - BTCUSDT no dash (Perpetual)"
)

# Test 6: Trade history
test_endpoint(
    "/openApi/swap/v2/trade/fillHistory",
    {},
    "Fill History (Perpetual)"
)

# Test 7: Income/PnL history
test_endpoint(
    "/openApi/swap/v2/user/income",
    {},
    "Income History (Perpetual)"
)

# Test 8: Commission history
test_endpoint(
    "/openApi/swap/v2/user/commissionRate",
    {'symbol': 'BTC-USDT'},
    "Commission Rate (Perpetual)"
)

# Test 9: Position history
test_endpoint(
    "/openApi/swap/v2/trade/allPositions",
    {},
    "All Positions History (Perpetual)"
)

# Test 10: Force orders
test_endpoint(
    "/openApi/swap/v2/trade/forceOrders",
    {},
    "Force Orders (Perpetual)"
)

print("\n" + "="*80)
print("  SPOT TRADING ENDPOINTS")
print("="*80)

# Test 11: Spot open orders
test_endpoint(
    "/openApi/spot/v1/trade/openOrders",
    {},
    "Spot Open Orders"
)

# Test 12: Spot all orders
test_endpoint(
    "/openApi/spot/v1/trade/allOrders",
    {'symbol': 'BTC-USDT'},
    "Spot All Orders - BTC-USDT"
)

# Test 13: Spot history orders
test_endpoint(
    "/openApi/spot/v1/trade/historyOrders",
    {},
    "Spot History Orders"
)

# Test 14: Spot my trades
test_endpoint(
    "/openApi/spot/v1/trade/myTrades",
    {'symbol': 'BTC-USDT'},
    "Spot My Trades - BTC-USDT"
)

print("\n" + "="*80)
print("  CHECKING ACCOUNT INFO")
print("="*80)

# Test 15: Account info
test_endpoint(
    "/openApi/swap/v2/user/balance",
    {},
    "Perpetual Account Balance"
)

# Test 16: Spot account
test_endpoint(
    "/openApi/spot/v1/account/balance",
    {},
    "Spot Account Balance"
)

print("\n" + "="*80)
print("  ✅ KIỂM TRA HOÀN TẤT")
print("="*80)
print("\nNếu có endpoint nào trả về data, đó là endpoint đúng!")
