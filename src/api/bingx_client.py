import hmac
import hashlib
import time
import requests
import logging
from typing import Dict, List, Optional
from urllib.parse import urlencode

logger = logging.getLogger(__name__)

class BingXClient:
    """BingX API Client - Read-only operations"""

    def __init__(self, api_key: str, secret_key: str, base_url: str = "https://open-api.bingx.com"):
        self.api_key = api_key
        self.secret_key = secret_key
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'X-BX-APIKEY': self.api_key,
            'Content-Type': 'application/json'
        })

    def _generate_signature(self, params: Dict) -> str:
        """Generate HMAC SHA256 signature for BingX API"""
        # Sort parameters and create query string
        query_string = '&'.join([f"{k}={params[k]}" for k in sorted(params.keys())])

        # Generate signature
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature

    def _request(self, method: str, endpoint: str, params: Optional[Dict] = None, signed: bool = True) -> Dict:
        """Make API request"""
        url = f"{self.base_url}{endpoint}"

        if params is None:
            params = {}

        if signed:
            params['timestamp'] = int(time.time() * 1000)
            # Generate signature BEFORE adding it to params
            signature = self._generate_signature(params)
            params['signature'] = signature

        try:
            if method == 'GET':
                response = self.session.get(url, params=params)
            elif method == 'POST':
                response = self.session.post(url, json=params)
            else:
                raise ValueError(f"Unsupported method: {method}")

            response.raise_for_status()
            data = response.json()

            if data.get('code') != 0:
                logger.error(f"API error: {data.get('msg')}")
                raise Exception(f"BingX API error: {data.get('msg')}")

            return data

        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise

    def get_account_info(self) -> Dict:
        """Get account information"""
        return self._request('GET', '/openApi/swap/v2/user/balance')

    def get_trade_history(self, symbol: str, start_time: Optional[int] = None,
                         end_time: Optional[int] = None, limit: int = 500) -> List[Dict]:
        """
        Get historical trades

        Args:
            symbol: Trading pair (e.g., 'BTC-USDT')
            start_time: Start timestamp in milliseconds
            end_time: End timestamp in milliseconds
            limit: Number of records (max 500)

        Returns:
            List of trade records
        """
        params = {
            'symbol': symbol,
            'limit': limit
        }

        if start_time:
            params['startTime'] = start_time
        if end_time:
            params['endTime'] = end_time

        response = self._request('GET', '/openApi/swap/v2/trade/allOrders', params)
        return response.get('data', {}).get('orders', [])

    def get_position_history(self, symbol: Optional[str] = None) -> List[Dict]:
        """Get position history"""
        params = {}
        if symbol:
            params['symbol'] = symbol

        response = self._request('GET', '/openApi/swap/v2/trade/allPositions', params)
        return response.get('data', [])

    def get_klines(self, symbol: str, interval: str = '1h', limit: int = 500,
                   start_time: Optional[int] = None, end_time: Optional[int] = None) -> List[Dict]:
        """
        Get candlestick data

        Args:
            symbol: Trading pair (e.g., 'BTC-USDT')
            interval: Timeframe (1m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 12h, 1d, 1w)
            limit: Number of candles (max 1440)
            start_time: Start timestamp in milliseconds
            end_time: End timestamp in milliseconds

        Returns:
            List of OHLCV data
        """
        params = {
            'symbol': symbol,
            'interval': interval,
            'limit': limit
        }

        if start_time:
            params['startTime'] = start_time
        if end_time:
            params['endTime'] = end_time

        response = self._request('GET', '/openApi/swap/v3/quote/klines', params, signed=False)
        return response.get('data', [])

    def get_ticker_price(self, symbol: Optional[str] = None) -> Dict:
        """Get current ticker price"""
        params = {}
        if symbol:
            params['symbol'] = symbol

        response = self._request('GET', '/openApi/swap/v2/quote/price', params, signed=False)
        return response.get('data', {})

    def get_all_positions(self) -> List[Dict]:
        """Get all current positions"""
        response = self._request('GET', '/openApi/swap/v2/user/positions')
        return response.get('data', [])

    def get_income_history(self, symbol: Optional[str] = None, income_type: Optional[str] = None,
                          start_time: Optional[int] = None, end_time: Optional[int] = None,
                          limit: int = 100) -> List[Dict]:
        """
        Get income history (PnL records)

        Args:
            symbol: Trading pair
            income_type: Type of income (REALIZED_PNL, FUNDING_FEE, etc.)
            start_time: Start timestamp
            end_time: End timestamp
            limit: Number of records

        Returns:
            List of income records
        """
        params = {'limit': limit}

        if symbol:
            params['symbol'] = symbol
        if income_type:
            params['incomeType'] = income_type
        if start_time:
            params['startTime'] = start_time
        if end_time:
            params['endTime'] = end_time

        response = self._request('GET', '/openApi/swap/v2/user/income', params)
        return response.get('data', [])

    def get_24hr_tickers(self) -> List[Dict]:
        """
        Get 24hr ticker price change statistics for all symbols

        Returns:
            List of tickers with fields:
            - symbol: Trading pair
            - priceChangePercent: 24h % change
            - volume: 24h volume
            - lastPrice: Current price
        """
        try:
            response = self._request('GET', '/openApi/swap/v2/quote/ticker',
                                   params={}, signed=False)
            return response.get('data', [])
        except Exception as e:
            logger.error(f"Failed to get 24hr tickers: {e}")
            return []

    def test_connection(self) -> bool:
        """Test API connection and credentials"""
        try:
            self.get_account_info()
            logger.info("BingX API connection successful")
            return True
        except Exception as e:
            logger.error(f"BingX API connection failed: {e}")
            return False
