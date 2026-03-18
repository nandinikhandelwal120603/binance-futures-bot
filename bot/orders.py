"""
Order placement logic for the Trading Bot.

Provides a high-level interface for placing MARKET, LIMIT, and STOP_LIMIT
orders on Binance Futures Testnet. Handles parameter construction,
response formatting, and human-readable output.
"""

import logging
from typing import Any, Dict, Optional

from .client import BinanceClient, BinanceClientError
from .validators import validate_all, ValidationError

logger = logging.getLogger("trading_bot")


# ── Pretty-print helpers ──

SEPARATOR = "─" * 52


def _format_order_summary(params: dict) -> str:
    """Format a human-readable order request summary."""
    lines = [
        "",
        f"┌{SEPARATOR}┐",
        f"│  📋  ORDER REQUEST SUMMARY{' ' * 25}│",
        f"├{SEPARATOR}┤",
        f"│  Symbol     : {params['symbol']:<36}│",
        f"│  Side       : {params['side']:<36}│",
        f"│  Type       : {params['order_type']:<36}│",
        f"│  Quantity   : {str(params['quantity']):<36}│",
    ]
    if params.get("price") is not None:
        lines.append(f"│  Price      : {str(params['price']):<36}│")
    if params.get("stop_price") is not None:
        lines.append(f"│  Stop Price : {str(params['stop_price']):<36}│")
    lines.append(f"└{SEPARATOR}┘")
    return "\n".join(lines)


def _format_order_response(response: dict) -> str:
    """Format a human-readable order response summary."""
    status = response.get("status", "UNKNOWN")
    order_id = response.get("orderId", "N/A")
    executed_qty = response.get("executedQty", "0")
    avg_price = response.get("avgPrice", response.get("price", "N/A"))
    client_order_id = response.get("clientOrderId", "N/A")
    order_type = response.get("type", "N/A")
    side = response.get("side", "N/A")
    symbol = response.get("symbol", "N/A")

    lines = [
        "",
        f"┌{SEPARATOR}┐",
        f"│  ✅  ORDER RESPONSE{' ' * 32}│",
        f"├{SEPARATOR}┤",
        f"│  Order ID       : {str(order_id):<31}│",
        f"│  Client Order ID: {str(client_order_id):<31}│",
        f"│  Symbol          : {symbol:<31}│",
        f"│  Side            : {side:<31}│",
        f"│  Type            : {order_type:<31}│",
        f"│  Status          : {status:<31}│",
        f"│  Executed Qty    : {str(executed_qty):<31}│",
        f"│  Avg Price       : {str(avg_price):<31}│",
        f"└{SEPARATOR}┘",
    ]
    return "\n".join(lines)


def _format_error(error_msg: str) -> str:
    """Format a human-readable error message."""
    lines = [
        "",
        f"┌{SEPARATOR}┐",
        f"│  ❌  ORDER FAILED{' ' * 34}│",
        f"├{SEPARATOR}┤",
    ]
    # Wrap long error messages
    while error_msg:
        chunk = error_msg[:48]
        error_msg = error_msg[48:]
        lines.append(f"│  {chunk:<50}│")
    lines.append(f"└{SEPARATOR}┘")
    return "\n".join(lines)


# ── Order Placement Functions ──


def place_order(
    client: BinanceClient,
    symbol: str,
    side: str,
    order_type: str,
    quantity: float,
    price: Optional[float] = None,
    stop_price: Optional[float] = None,
    time_in_force: str = "GTC",
) -> Dict[str, Any]:
    """
    Validate inputs and place an order on Binance Futures Testnet.

    This is the main entry point for order placement. It:
    1. Validates all inputs
    2. Prints the order request summary
    3. Sends the order to the API
    4. Prints the response or error
    5. Returns the API response

    Args:
        client: Initialized BinanceClient instance.
        symbol: Trading pair (e.g., 'BTCUSDT').
        side: Order side ('BUY' or 'SELL').
        order_type: Order type ('MARKET', 'LIMIT', or 'STOP_LIMIT').
        quantity: Amount to trade.
        price: Limit price (required for LIMIT/STOP_LIMIT).
        stop_price: Stop trigger price (required for STOP_LIMIT).
        time_in_force: Time-in-force policy (default: 'GTC').

    Returns:
        Dict with the Binance API order response.

    Raises:
        ValidationError: If input validation fails.
        BinanceClientError: If the API returns an error.
    """
    # ── Step 1: Validate ──
    logger.info("Validating order parameters...")
    validated = validate_all(
        symbol=symbol,
        side=side,
        order_type=order_type,
        quantity=quantity,
        price=price,
        stop_price=stop_price,
    )

    # ── Step 2: Print summary ──
    summary = _format_order_summary(validated)
    print(summary)
    logger.info("Order summary:%s", summary)

    # ── Step 3: Build API params ──
    api_params = {
        "symbol": validated["symbol"],
        "side": validated["side"],
        "type": validated["order_type"] if validated["order_type"] != "STOP_LIMIT" else "STOP",
        "quantity": validated["quantity"],
    }

    # For LIMIT orders → add price + timeInForce
    if validated["order_type"] == "LIMIT":
        api_params["price"] = validated["price"]
        api_params["timeInForce"] = time_in_force

    # For STOP_LIMIT orders → add price + stopPrice + timeInForce
    if validated["order_type"] == "STOP_LIMIT":
        api_params["type"] = "STOP"
        api_params["price"] = validated["price"]
        api_params["stopPrice"] = validated["stop_price"]
        api_params["timeInForce"] = time_in_force

    logger.debug("API order params: %s", api_params)

    # ── Step 4: Place the order ──
    try:
        logger.info("Sending order to Binance Futures Testnet...")
        response = client.place_order(**api_params)

        # ── Step 5: Print response ──
        response_text = _format_order_response(response)
        print(response_text)
        logger.info("Order response:%s", response_text)
        print("\n  🎉 Order placed successfully!\n")
        logger.info("Order placed successfully: orderId=%s", response.get("orderId"))

        return response

    except BinanceClientError as e:
        error_text = _format_error(str(e))
        print(error_text)
        logger.error("Order placement failed: %s", e)
        raise

    except Exception as e:
        error_text = _format_error(f"Unexpected error: {e}")
        print(error_text)
        logger.exception("Unexpected error during order placement")
        raise
