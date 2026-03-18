"""
Binance Futures Testnet API Client.

Handles authentication (HMAC-SHA256 signing), request construction,
and communication with the Binance Futures Testnet REST API.
"""

import hashlib
import hmac
import logging
import time
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import requests

logger = logging.getLogger("trading_bot")

# ── Testnet Configuration ──
BASE_URL = "https://testnet.binancefuture.com"
API_VERSION = "/fapi/v1"


class BinanceClientError(Exception):
    """Raised when the Binance API returns an error response."""

    def __init__(self, status_code: int, error_code: int, message: str):
        self.status_code = status_code
        self.error_code = error_code
        self.message = message
        super().__init__(f"[HTTP {status_code}] Binance Error {error_code}: {message}")


class BinanceClient:
    """
    Low-level wrapper around the Binance Futures Testnet REST API.

    Handles:
    - HMAC-SHA256 request signing
    - Timestamp synchronization
    - HTTP error handling and retries
    - Structured logging of all API interactions
    """

    def __init__(self, api_key: str, api_secret: str, base_url: str = BASE_URL):
        """
        Initialize the Binance client.

        Args:
            api_key: Binance API key.
            api_secret: Binance API secret.
            base_url: API base URL (defaults to testnet).
        """
        if not api_key or not api_secret:
            raise ValueError("API key and secret must not be empty.")

        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({
            "X-MBX-APIKEY": self.api_key,
            "Content-Type": "application/x-www-form-urlencoded",
        })
        logger.info("BinanceClient initialized → %s", self.base_url)

    def _generate_signature(self, params: Dict[str, Any]) -> str:
        """
        Generate HMAC-SHA256 signature for a request.

        Args:
            params: Query parameters to sign.

        Returns:
            Hex-encoded signature string.
        """
        query_string = urlencode(params)
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return signature

    def _build_signed_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add timestamp and signature to parameters.

        Args:
            params: Original request parameters.

        Returns:
            Parameters with timestamp and signature appended.
        """
        params["timestamp"] = int(time.time() * 1000)
        params["signature"] = self._generate_signature(params)
        return params

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        signed: bool = True,
    ) -> Dict[str, Any]:
        """
        Execute an API request.

        Args:
            method: HTTP method (GET, POST, DELETE).
            endpoint: API endpoint path (e.g., '/fapi/v1/order').
            params: Request parameters.
            signed: Whether to sign the request.

        Returns:
            Parsed JSON response.

        Raises:
            BinanceClientError: If the API returns an error.
            requests.RequestException: On network failures.
        """
        params = params or {}
        url = f"{self.base_url}{endpoint}"

        if signed:
            params = self._build_signed_params(params)

        logger.debug("API Request: %s %s | Params: %s", method, url, params)

        try:
            response = self.session.request(method, url, params=params, timeout=30)
        except requests.ConnectionError as e:
            logger.error("Network error connecting to %s: %s", url, e)
            raise
        except requests.Timeout as e:
            logger.error("Request to %s timed out: %s", url, e)
            raise
        except requests.RequestException as e:
            logger.error("Unexpected request error: %s", e)
            raise

        logger.debug("API Response [%d]: %s", response.status_code, response.text[:500])

        # ── Handle API errors ──
        if response.status_code != 200:
            try:
                error_data = response.json()
                error_code = error_data.get("code", -1)
                error_msg = error_data.get("msg", "Unknown error")
            except ValueError:
                error_code = -1
                error_msg = response.text

            logger.error(
                "API Error: HTTP %d | Code %d | %s",
                response.status_code, error_code, error_msg,
            )
            raise BinanceClientError(response.status_code, error_code, error_msg)

        return response.json()

    # ── Public API Methods ──

    def ping(self) -> bool:
        """Test connectivity to the API."""
        try:
            self._request("GET", f"{API_VERSION}/ping", signed=False)
            logger.info("API ping successful ✓")
            return True
        except Exception as e:
            logger.error("API ping failed: %s", e)
            return False

    def get_server_time(self) -> int:
        """Get the server time in milliseconds."""
        data = self._request("GET", f"{API_VERSION}/time", signed=False)
        return data["serverTime"]

    def get_ticker_price(self, symbol: str) -> Dict[str, Any]:
        """
        Get the latest price for a symbol.

        Args:
            symbol: Trading pair (e.g., 'BTCUSDT').

        Returns:
            Dict with 'symbol' and 'price' keys.
        """
        return self._request(
            "GET", f"{API_VERSION}/ticker/price",
            params={"symbol": symbol}, signed=False,
        )

    def get_account_info(self) -> Dict[str, Any]:
        """Get current account information (balances, positions)."""
        return self._request("GET", "/fapi/v2/account")

    def place_order(self, **kwargs) -> Dict[str, Any]:
        """
        Place a new order on Binance Futures.

        Args:
            **kwargs: Order parameters (symbol, side, type, quantity, etc.)

        Returns:
            Order response dict from Binance.
        """
        return self._request("POST", f"{API_VERSION}/order", params=kwargs)

    def get_order(self, symbol: str, order_id: int) -> Dict[str, Any]:
        """
        Query an existing order.

        Args:
            symbol: Trading pair.
            order_id: The order ID to query.

        Returns:
            Order details dict.
        """
        return self._request(
            "GET", f"{API_VERSION}/order",
            params={"symbol": symbol, "orderId": order_id},
        )

    def cancel_order(self, symbol: str, order_id: int) -> Dict[str, Any]:
        """
        Cancel an active order.

        Args:
            symbol: Trading pair.
            order_id: The order ID to cancel.

        Returns:
            Cancellation response dict.
        """
        return self._request(
            "DELETE", f"{API_VERSION}/order",
            params={"symbol": symbol, "orderId": order_id},
        )

    def get_open_orders(self, symbol: Optional[str] = None) -> list:
        """
        Get all open orders, optionally filtered by symbol.

        Args:
            symbol: Optional trading pair filter.

        Returns:
            List of open order dicts.
        """
        params = {}
        if symbol:
            params["symbol"] = symbol
        return self._request("GET", f"{API_VERSION}/openOrders", params=params)
