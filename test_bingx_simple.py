#!/usr/bin/env python3
"""
Simple BingX API test để kiểm tra kết nối
"""

import hmac
import hashlib
import time
import requests
from urllib.parse import urlencode

# API credentials
API_KEY = "K5tdJ7lJ7e45gF0r9T0OOsHQrdyg0XGHrZ6vT5CQ8DFriubLnHCyH8kxd3zb8sw2b8qBm2l2tq9fbYIPrNQ9w"
SECRET_KEY = "aSMSk0rwMALgF7M3yk3lnXQ9pVAiMZj3Qmh7YsMmG8NQCmuW8ebJ2Jbr0ROv23aJ4y2tUObjn3v0YHYYkkg"
BASE_URL = "https://open-api.bingx.com"

def generate_signature(params, secret):
    """Generate signature"""
    query_string = '&'.join([f"{k}={params[k]}" for k in sorted(params.keys())])
    print(f"Query string: {query_string}")

    signature = hmac.new(
        secret.encode('utf-8'),
        query_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return signature

# Test 1: Get account balance (Perpetual Swap)
print("=" * 70)
print("Test 1: Get Account Balance (Perpetual Swap)")
print("=" * 70)

params = {
    'timestamp': int(time.time() * 1000)
}

signature = generate_signature(params, SECRET_KEY)
params['signature'] = signature

headers = {
    'X-BX-APIKEY': API_KEY
}

url = f"{BASE_URL}/openApi/swap/v2/user/balance"
print(f"URL: {url}")
print(f"Params: {params}")

response = requests.get(url, params=params, headers=headers)
print(f"Status: {response.status_code}")
print(f"Response: {response.text}\n")

# Test 2: Get positions
print("=" * 70)
print("Test 2: Get Positions")
print("=" * 70)

params = {
    'timestamp': int(time.time() * 1000)
}

signature = generate_signature(params, SECRET_KEY)
params['signature'] = signature

url = f"{BASE_URL}/openApi/swap/v2/user/positions"
response = requests.get(url, params=params, headers=headers)
print(f"Status: {response.status_code}")
print(f"Response: {response.text}\n")

# Test 3: Get trade history
print("=" * 70)
print("Test 3: Get Trade History (BTC-USDT)")
print("=" * 70)

params = {
    'symbol': 'BTC-USDT',
    'timestamp': int(time.time() * 1000)
}

signature = generate_signature(params, SECRET_KEY)
params['signature'] = signature

url = f"{BASE_URL}/openApi/swap/v2/trade/allOrders"
response = requests.get(url, params=params, headers=headers)
print(f"Status: {response.status_code}")
print(f"Response: {response.text}\n")

# Test 4: Get income history
print("=" * 70)
print("Test 4: Get Income History")
print("=" * 70)

params = {
    'timestamp': int(time.time() * 1000)
}

signature = generate_signature(params, SECRET_KEY)
params['signature'] = signature

url = f"{BASE_URL}/openApi/swap/v2/user/income"
response = requests.get(url, params=params, headers=headers)
print(f"Status: {response.status_code}")
print(f"Response: {response.text}\n")
