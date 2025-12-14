#!/usr/bin/env python3
"""
Debug: Kiểm tra tất cả cách lấy data từ Standard Futures
"""

import hmac
import hashlib
import time
import requests
import json
from datetime import datetime

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

def test_endpoint(endpoint, params_dict=None, description=""):
    """Test endpoint và show full response"""
    print(f"\n{'='*80}")
    print(f"Testing: {description}")
    print(f"Endpoint: {endpoint}")
    print(f"{'='*80}")

    if params_dict is None:
        params_dict = {}

    params = {'timestamp': int(time.time() * 1000)}
    params.update(params_dict)

    signature = generate_signature(params, SECRET_KEY)
    params['signature'] = signature

    headers = {'X-BX-APIKEY': API_KEY}

    url = f"{BASE_URL}{endpoint}"
    print(f"URL: {url}")
    print(f"Params: {params}")

    response = requests.get(url, params=params, headers=headers)

    print(f"\nStatus: {response.status_code}")

    try:
        data = response.json()

        if data.get('code') == 0:
            print(f"✅ SUCCESS")

            # Count results
            result_data = data.get('data')
            if isinstance(result_data, list):
                print(f"📊 Records: {len(result_data)}")
                if len(result_data) > 0:
                    print(f"\n📋 Sample record:")
                    print(json.dumps(result_data[0], indent=2))

                    # Show time range
                    if 'time' in result_data[0]:
                        times = [r.get('time', 0) for r in result_data]
                        oldest = datetime.fromtimestamp(min(times)/1000)
                        newest = datetime.fromtimestamp(max(times)/1000)
                        print(f"\n⏰ Time range: {oldest.strftime('%Y-%m-%d')} to {newest.strftime('%Y-%m-%d')}")

            elif isinstance(result_data, dict):
                if 'orders' in result_data:
                    print(f"📊 Orders: {len(result_data['orders'])}")
                    if result_data['orders']:
                        print(f"\n📋 Sample order:")
                        print(json.dumps(result_data['orders'][0], indent=2))
                else:
                    print(f"📊 Data: {json.dumps(result_data, indent=2)}")
            else:
                print(f"Response: {data}")

            return result_data
        else:
            print(f"❌ Error: {data.get('msg')}")
            return None

    except Exception as e:
        print(f"Error: {e}")
        print(f"Raw: {response.text[:500]}")
        return None

print("="*80)
print("  🔍 DEBUG: LẤY TOÀN BỘ DATA TỪ STANDARD FUTURES")
print("="*80)

# Test 1: Basic call - no limit
print("\n\n" + "="*80)
print("  TEST 1: BASIC CALL - NO LIMIT")
print("="*80)

data1 = test_endpoint(
    "/openApi/contract/v1/allOrders",
    {},
    "All Orders - No params"
)

# Test 2: With high limit
print("\n\n" + "="*80)
print("  TEST 2: WITH HIGH LIMIT")
print("="*80)

data2 = test_endpoint(
    "/openApi/contract/v1/allOrders",
    {'limit': 1000},
    "All Orders - Limit 1000"
)

# Test 3: Check if there are more endpoints
print("\n\n" + "="*80)
print("  TEST 3: TRY OTHER POSSIBLE ENDPOINTS")
print("="*80)

# Historical orders
test_endpoint(
    "/openApi/contract/v1/historyOrders",
    {},
    "History Orders (if exists)"
)

# All fills
test_endpoint(
    "/openApi/contract/v1/allFills",
    {},
    "All Fills (if exists)"
)

# User trades
test_endpoint(
    "/openApi/contract/v1/userTrades",
    {},
    "User Trades (if exists)"
)

# Test 4: Try paginated approach
print("\n\n" + "="*80)
print("  TEST 4: CHECK PAGINATION")
print("="*80)

# If first call returned data, check if there's more
if data1:
    if isinstance(data1, list) and len(data1) >= 10:
        print("⚠️ Có thể có thêm data. Thử pagination...")

        # Get oldest order
        if 'orderId' in data1[-1]:
            oldest_id = data1[-1]['orderId']

            test_endpoint(
                "/openApi/contract/v1/allOrders",
                {'orderId': oldest_id},
                "Paginate from oldest orderId"
            )

# Test 5: Try income/PnL endpoint for complete history
print("\n\n" + "="*80)
print("  TEST 5: INCOME/PNL HISTORY")
print("="*80)

test_endpoint(
    "/openApi/swap/v2/user/income",
    {'limit': 1000},
    "Income History - Limit 1000"
)

# Test 6: Try v3 if exists
print("\n\n" + "="*80)
print("  TEST 6: TRY V3 ENDPOINTS")
print("="*80)

test_endpoint(
    "/openApi/contract/v3/allOrders",
    {},
    "All Orders V3 (if exists)"
)

# Summary
print("\n\n" + "="*80)
print("  📊 SUMMARY")
print("="*80)

if data1:
    if isinstance(data1, list):
        print(f"\n✅ Endpoint hoạt động: /openApi/contract/v1/allOrders")
        print(f"📊 Số lệnh hiện tại: {len(data1)}")

        if len(data1) >= 10:
            print(f"\n⚠️ CÓ THỂ THIẾU DATA:")
            print(f"   • API có thể chỉ trả về {len(data1)} lệnh gần nhất")
            print(f"   • Cần check xem có pagination không")
            print(f"   • Hoặc cần dùng endpoint khác")
        else:
            print(f"\n✅ Đây có thể là toàn bộ data của bạn")

    # Count SHORT
    if isinstance(data1, list):
        shorts = [o for o in data1 if o.get('positionSide') == 'SHORT']
        print(f"\n📊 Lệnh SHORT: {len(shorts)}/{len(data1)}")

print("\n" + "="*80)
