"""
Configuration loader for the Trading Bot.

Reads API credentials from environment variables or a .env file.
"""

import os
import logging

logger = logging.getLogger("trading_bot")


class ConfigError(Exception):
    """Raised when required configuration is missing."""
    pass


def load_config() -> dict:
    """
    Load configuration from environment variables.

    Attempts to load from a .env file first (if python-dotenv is installed),
    then reads from the environment.

    Returns:
        Dict with 'api_key', 'api_secret', and 'base_url'.

    Raises:
        ConfigError: If API key or secret is missing.
    """
    # Try loading .env file
    try:
        from dotenv import load_dotenv
        env_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            ".env"
        )
        load_dotenv(env_path)
        logger.info("Loaded .env file from %s", env_path)
    except ImportError:
        logger.debug("python-dotenv not installed, using system environment only.")

    api_key = os.environ.get("BINANCE_API_KEY", "").strip()
    api_secret = os.environ.get("BINANCE_API_SECRET", "").strip()
    base_url = os.environ.get(
        "BINANCE_BASE_URL",
        "https://testnet.binancefuture.com"
    ).strip()

    if not api_key:
        raise ConfigError(
            "BINANCE_API_KEY is not set. "
            "Set it as an environment variable or in a .env file."
        )
    if not api_secret:
        raise ConfigError(
            "BINANCE_API_SECRET is not set. "
            "Set it as an environment variable or in a .env file."
        )

    logger.info("Configuration loaded (API key: %s...)", api_key[:8])
    return {
        "api_key": api_key,
        "api_secret": api_secret,
        "base_url": base_url,
    }
