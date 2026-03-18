#!/usr/bin/env python3
"""
Binance Futures Testnet Trading Bot — CLI Entry Point.

Usage examples:
    # Market order
    python main.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001

    # Limit order
    python main.py --symbol ETHUSDT --side SELL --type LIMIT --quantity 0.05 --price 3500

    # Stop-Limit order
    python main.py --symbol BTCUSDT --side SELL --type STOP_LIMIT --quantity 0.001 --price 59000 --stop-price 60000

    # Check connectivity
    python main.py --ping

    # Get current price
    python main.py --price BTCUSDT

    # View account info
    python main.py --account
"""

import argparse
import sys

from bot.logging_config import setup_logging
from bot.config import load_config, ConfigError
from bot.client import BinanceClient, BinanceClientError
from bot.orders import place_order
from bot.validators import ValidationError


# ── Banner ──
BANNER = r"""
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║   ₿  Binance Futures Testnet — Trading Bot  ₿           ║
║                                                          ║
║   Place MARKET, LIMIT, and STOP_LIMIT orders             ║
║   on the Binance Futures USDT-M Testnet.                 ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
"""


def build_parser() -> argparse.ArgumentParser:
    """Build and return the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="trading_bot",
        description="Binance Futures Testnet Trading Bot — Place orders via CLI.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001
  %(prog)s --symbol ETHUSDT --side SELL --type LIMIT --quantity 0.05 --price 3500
  %(prog)s --symbol BTCUSDT --side SELL --type STOP_LIMIT --quantity 0.001 --price 59000 --stop-price 60000
  %(prog)s --ping
  %(prog)s --price BTCUSDT
  %(prog)s --account
        """,
    )

    # ── Utility commands ──
    util_group = parser.add_argument_group("Utility Commands")
    util_group.add_argument(
        "--ping", action="store_true",
        help="Test API connectivity and exit.",
    )
    util_group.add_argument(
        "--ticker", metavar="SYMBOL", type=str,
        help="Get the current price for a symbol (e.g., BTCUSDT).",
    )
    util_group.add_argument(
        "--account", action="store_true",
        help="Display account information (balances & positions).",
    )

    # ── Order parameters ──
    order_group = parser.add_argument_group("Order Parameters")
    order_group.add_argument(
        "--symbol", "-s", type=str,
        help="Trading pair symbol (e.g., BTCUSDT, ETHUSDT).",
    )
    order_group.add_argument(
        "--side", type=str, choices=["BUY", "SELL", "buy", "sell"],
        help="Order side: BUY or SELL.",
    )
    order_group.add_argument(
        "--type", "-t", type=str, dest="order_type",
        choices=["MARKET", "LIMIT", "STOP_LIMIT", "market", "limit", "stop_limit"],
        help="Order type: MARKET, LIMIT, or STOP_LIMIT.",
    )
    order_group.add_argument(
        "--quantity", "-q", type=float,
        help="Order quantity (e.g., 0.001 for BTC).",
    )
    order_group.add_argument(
        "--price", "-p", type=float, default=None,
        help="Limit price (required for LIMIT and STOP_LIMIT orders).",
    )
    order_group.add_argument(
        "--stop-price", type=float, default=None,
        help="Stop trigger price (required for STOP_LIMIT orders).",
    )
    order_group.add_argument(
        "--tif", type=str, default="GTC",
        choices=["GTC", "IOC", "FOK"],
        help="Time in force (default: GTC).",
    )

    # ── Logging ──
    parser.add_argument(
        "--log-level", type=str, default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Console log level (default: INFO).",
    )

    return parser


def handle_ping(client: BinanceClient) -> None:
    """Handle the --ping command."""
    if client.ping():
        print("\n  ✅  API connectivity OK\n")
    else:
        print("\n  ❌  API connectivity FAILED\n")
        sys.exit(1)


def handle_price(client: BinanceClient, symbol: str) -> None:
    """Handle the --price command."""
    try:
        data = client.get_ticker_price(symbol.upper())
        print(f"\n  💰  {data['symbol']}: ${data['price']}\n")
    except BinanceClientError as e:
        print(f"\n  ❌  Error fetching price: {e}\n")
        sys.exit(1)


def handle_account(client: BinanceClient) -> None:
    """Handle the --account command."""
    try:
        info = client.get_account_info()
        print("\n  📊  Account Summary")
        print("  " + "─" * 50)

        # Show USDT balance
        for asset in info.get("assets", []):
            if float(asset.get("walletBalance", 0)) > 0:
                print(
                    f"  {asset['asset']:>8s}  │  "
                    f"Balance: {asset['walletBalance']:>14s}  │  "
                    f"Available: {asset['availableBalance']:>14s}"
                )

        # Show open positions
        positions = [p for p in info.get("positions", []) if float(p.get("positionAmt", 0)) != 0]
        if positions:
            print("\n  📈  Open Positions")
            print("  " + "─" * 50)
            for pos in positions:
                print(
                    f"  {pos['symbol']:>10s}  │  "
                    f"Amt: {pos['positionAmt']:>12s}  │  "
                    f"Entry: {pos['entryPrice']:>12s}  │  "
                    f"PnL: {pos['unrealizedProfit']:>12s}"
                )
        else:
            print("\n  ℹ️   No open positions.")

        print()
    except BinanceClientError as e:
        print(f"\n  ❌  Error fetching account info: {e}\n")
        sys.exit(1)


def handle_order(client: BinanceClient, args: argparse.Namespace) -> None:
    """Handle order placement."""
    # Validate required fields are present
    missing = []
    if not args.symbol:
        missing.append("--symbol")
    if not args.side:
        missing.append("--side")
    if not args.order_type:
        missing.append("--type")
    if args.quantity is None:
        missing.append("--quantity")

    if missing:
        print(f"\n  ❌  Missing required arguments: {', '.join(missing)}")
        print("  Use --help for usage information.\n")
        sys.exit(1)

    try:
        place_order(
            client=client,
            symbol=args.symbol,
            side=args.side,
            order_type=args.order_type,
            quantity=args.quantity,
            price=args.price,
            stop_price=args.stop_price,
            time_in_force=args.tif,
        )
    except ValidationError as e:
        print(f"\n  ❌  Validation Error: {e}\n")
        sys.exit(1)
    except BinanceClientError:
        # Already printed by place_order
        sys.exit(1)
    except Exception as e:
        print(f"\n  ❌  Unexpected Error: {e}\n")
        sys.exit(1)


def main():
    """Main entry point for the trading bot CLI."""
    parser = build_parser()
    args = parser.parse_args()

    print(BANNER)

    # ── Setup logging ──
    logger = setup_logging(log_level=args.log_level)

    # ── Load configuration ──
    try:
        config = load_config()
    except ConfigError as e:
        print(f"\n  ❌  Configuration Error: {e}\n")
        sys.exit(1)

    # ── Initialize client ──
    client = BinanceClient(
        api_key=config["api_key"],
        api_secret=config["api_secret"],
        base_url=config["base_url"],
    )

    # ── Route to the appropriate handler ──
    if args.ping:
        handle_ping(client)
    elif args.ticker:
        handle_price(client, args.ticker)
    elif args.account:
        handle_account(client)
    else:
        handle_order(client, args)


if __name__ == "__main__":
    main()
