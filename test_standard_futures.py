#!/usr/bin/env python3
"""
Test Standard Futures endpoints
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
            response_data = data.get('data')
            if response_data:
                # Check if it's a list or dict with content
                if isinstance(response_data, list) and len(response_data) > 0:
                    print(f"✅ HAS DATA! Found {len(response_data)} items")
                    return True
                elif isinstance(response_data, dict):
                    if 'orders' in response_data and response_data['orders']:
                        print(f"✅ HAS DATA! Found {len(response_data['orders'])} orders")
                        return True
                    elif 'fills' in response_data and response_data['fills']:
                        print(f"✅ HAS DATA! Found {len(response_data['fills'])} fills")
                        return True
                    elif response_data:
                        print(f"✅ HAS DATA!")
                        return True
        else:
            print(f"❌ Error: {data.get('msg')}")
    except Exception as e:
        print(f"Error parsing: {e}")
        print(f"Raw response: {response.text}")

    return False

print("\n" + "="*80)
print("  🔍 TEST STANDARD FUTURES ENDPOINTS")
print("="*80)

# First, get available contracts
print("\n" + "="*80)
print("  📋 STEP 1: GET AVAILABLE STANDARD FUTURES CONTRACTS")
print("="*80)

# Test with v3 API
test_endpoint(
    "/openApi/swap/v3/quote/contracts",
    {},
    "Get All Contracts (v3)"
)

# Test Standard Futures balance
test_endpoint(
    "/openApi/swap/v2/user/balance",
    {},
    "Standard Futures Balance"
)

# Test with different possible endpoints
endpoints_to_test = [
    # Standard contract endpoints
    ("/openApi/contract/v1/allOrders", {}, "Standard Contract All Orders (v1)"),
    ("/openApi/contract/allOrders", {}, "Standard Contract All Orders"),

    # Try v3 endpoints
    ("/openApi/swap/v3/trade/allOrders", {}, "All Orders (v3)"),
    ("/openApi/swap/v3/trade/openOrders", {}, "Open Orders (v3)"),
    ("/openApi/swap/v3/user/balance", {}, "Balance (v3)"),

    # Historical data
    ("/openApi/swap/v3/trade/fillHistory", {}, "Fill History (v3)"),

    # Try without symbol first
    ("/openApi/swap/v2/trade/allOrders", {}, "All Orders No Symbol (v2)"),

    # Try with limit
    ("/openApi/swap/v2/trade/allOrders", {'limit': 100}, "All Orders with Limit (v2)"),

    # Income history
    ("/openApi/swap/v2/user/income", {'limit': 100}, "Income History (v2)"),
    ("/openApi/swap/v3/user/income", {}, "Income History (v3)"),
]

for endpoint, params, desc in endpoints_to_test:
    test_endpoint(endpoint, params, desc)
    time.sleep(0.5)

# Also try to get ticker/market data to see available symbols
print("\n" + "="*80)
print("  📊 GET MARKET DATA (To see active symbols)")
print("="*80)

# Get ticker price (no auth needed)
url = f"{BASE_URL}/openApi/swap/v2/quote/ticker"
response = requests.get(url)
print(f"\nTicker Price (Perpetual):")
print(f"Status: {response.status_code}")
try:
    data = response.json()
    if data.get('code') == 0 and data.get('data'):
        tickers = data['data']
        print(f"Found {len(tickers)} symbols")
        print("\nFirst 5 symbols:")
        for ticker in tickers[:5]:
            print(f"  - {ticker.get('symbol')}: ${ticker.get('lastPrice')}")
except:
    print(response.text[:500])

# Try v3 ticker
url = f"{BASE_URL}/openApi/swap/v3/quote/ticker"
response = requests.get(url)
print(f"\nTicker Price (v3):")
print(f"Status: {response.status_code}")
try:
    data = response.json()
    if data.get('code') == 0 and data.get('data'):
        tickers = data['data']
        print(f"Found {len(tickers)} symbols")
        print("\nFirst 5 symbols:")
        for ticker in tickers[:5]:
            print(f"  - {ticker.get('symbol')}: ${ticker.get('lastPrice')}")
except:
    print(response.text[:500])

print("\n" + "="*80)
print("  ✅ TEST COMPLETE")
print("="*80)
print("\n💡 Nếu vẫn không tìm thấy data:")
print("   1. Kiểm tra API key permissions trên BingX")
print("   2. Xem bạn đang trade symbol nào (BTC-USDT, ETH-USDT?)")
print("   3. Có thể cần dùng Web UI export data")
