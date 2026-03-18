"""
Input validators for trading bot CLI arguments.

Validates symbols, sides, order types, quantities, and prices
before they reach the API layer.
"""

import logging
from typing import Optional

logger = logging.getLogger("trading_bot")

# ── Constants ──
VALID_SIDES = ("BUY", "SELL")
VALID_ORDER_TYPES = ("MARKET", "LIMIT", "STOP_LIMIT")
SUPPORTED_SYMBOLS = (
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "DOGEUSDT",
    "SOLUSDT", "ADAUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT",
    "MATICUSDT", "LTCUSDT", "TRXUSDT", "UNIUSDT", "ATOMUSDT",
)


class ValidationError(Exception):
    """Raised when user input fails validation."""
    pass


def validate_symbol(symbol: str) -> str:
    """
    Validate and normalize a trading symbol.

    Args:
        symbol: Trading pair symbol (e.g., 'btcusdt').

    Returns:
        Upper-cased symbol string.

    Raises:
        ValidationError: If the symbol is not in the supported list.
    """
    symbol = symbol.strip().upper()
    if not symbol:
        raise ValidationError("Symbol cannot be empty.")
    if symbol not in SUPPORTED_SYMBOLS:
        raise ValidationError(
            f"Unsupported symbol: '{symbol}'. "
            f"Supported symbols: {', '.join(SUPPORTED_SYMBOLS)}"
        )
    logger.debug("Symbol validated: %s", symbol)
    return symbol


def validate_side(side: str) -> str:
    """
    Validate order side.

    Args:
        side: Order side ('BUY' or 'SELL').

    Returns:
        Upper-cased side string.

    Raises:
        ValidationError: If side is not BUY or SELL.
    """
    side = side.strip().upper()
    if side not in VALID_SIDES:
        raise ValidationError(
            f"Invalid side: '{side}'. Must be one of: {', '.join(VALID_SIDES)}"
        )
    logger.debug("Side validated: %s", side)
    return side


def validate_order_type(order_type: str) -> str:
    """
    Validate order type.

    Args:
        order_type: Type of order ('MARKET', 'LIMIT', or 'STOP_LIMIT').

    Returns:
        Upper-cased order type string.

    Raises:
        ValidationError: If order type is not supported.
    """
    order_type = order_type.strip().upper()
    if order_type not in VALID_ORDER_TYPES:
        raise ValidationError(
            f"Invalid order type: '{order_type}'. "
            f"Must be one of: {', '.join(VALID_ORDER_TYPES)}"
        )
    logger.debug("Order type validated: %s", order_type)
    return order_type


def validate_quantity(quantity: float) -> float:
    """
    Validate order quantity.

    Args:
        quantity: Number of units to trade.

    Returns:
        The validated quantity as a float.

    Raises:
        ValidationError: If quantity is not a positive number.
    """
    try:
        quantity = float(quantity)
    except (TypeError, ValueError):
        raise ValidationError(f"Quantity must be a number, got: '{quantity}'")

    if quantity <= 0:
        raise ValidationError(f"Quantity must be positive, got: {quantity}")

    logger.debug("Quantity validated: %s", quantity)
    return quantity


def validate_price(price: Optional[float], order_type: str) -> Optional[float]:
    """
    Validate price based on order type.

    - LIMIT and STOP_LIMIT orders require a price.
    - MARKET orders ignore the price.

    Args:
        price: The limit price (can be None for MARKET orders).
        order_type: The validated order type.

    Returns:
        The validated price as a float, or None for MARKET.

    Raises:
        ValidationError: If price is required but missing/invalid.
    """
    if order_type == "MARKET":
        if price is not None:
            logger.info("Price ignored for MARKET order.")
        return None

    # LIMIT and STOP_LIMIT require a price
    if price is None:
        raise ValidationError(f"Price is required for {order_type} orders.")

    try:
        price = float(price)
    except (TypeError, ValueError):
        raise ValidationError(f"Price must be a number, got: '{price}'")

    if price <= 0:
        raise ValidationError(f"Price must be positive, got: {price}")

    logger.debug("Price validated: %s", price)
    return price


def validate_stop_price(stop_price: Optional[float], order_type: str) -> Optional[float]:
    """
    Validate stop price for STOP_LIMIT orders.

    Args:
        stop_price: The stop trigger price.
        order_type: The validated order type.

    Returns:
        The validated stop price as a float, or None if not applicable.

    Raises:
        ValidationError: If stop price is required but missing/invalid.
    """
    if order_type != "STOP_LIMIT":
        return None

    if stop_price is None:
        raise ValidationError("Stop price is required for STOP_LIMIT orders.")

    try:
        stop_price = float(stop_price)
    except (TypeError, ValueError):
        raise ValidationError(f"Stop price must be a number, got: '{stop_price}'")

    if stop_price <= 0:
        raise ValidationError(f"Stop price must be positive, got: {stop_price}")

    logger.debug("Stop price validated: %s", stop_price)
    return stop_price


def validate_all(
    symbol: str,
    side: str,
    order_type: str,
    quantity: float,
    price: Optional[float] = None,
    stop_price: Optional[float] = None,
) -> dict:
    """
    Run all validators and return a clean parameter dict.

    Args:
        symbol: Trading pair symbol.
        side: Order side (BUY/SELL).
        order_type: Order type (MARKET/LIMIT/STOP_LIMIT).
        quantity: Number of units.
        price: Limit price (optional for MARKET).
        stop_price: Stop trigger price (required for STOP_LIMIT).

    Returns:
        Dict with validated parameters.

    Raises:
        ValidationError: If any validation fails.
    """
    validated_type = validate_order_type(order_type)
    return {
        "symbol": validate_symbol(symbol),
        "side": validate_side(side),
        "order_type": validated_type,
        "quantity": validate_quantity(quantity),
        "price": validate_price(price, validated_type),
        "stop_price": validate_stop_price(stop_price, validated_type),
    }
