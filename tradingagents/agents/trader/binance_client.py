"""Binance API helper for executing trades in paper or live modes."""

from binance.client import Client


class BinanceTrader:
    """Simple wrapper around the Binance Client to handle live and paper trading."""

    def __init__(self, api_key: str, api_secret: str, mode: str = "paper") -> None:
        self.testnet = mode.lower() == "paper"
        self.api_key = api_key
        self.api_secret = api_secret
        self._client = None

    def _get_client(self) -> Client:
        if self._client is None:
            self._client = Client(self.api_key, self.api_secret, testnet=self.testnet)
        return self._client

    def execute_trade(self, symbol: str, side: str, quantity: float):
        """Execute a market order on Binance.

        Args:
            symbol: Trading pair symbol, e.g. "BTCUSDT".
            side: "BUY" or "SELL".
            quantity: Amount to trade.
        """
        order_params = {
            "symbol": symbol,
            "side": side.upper(),
            "type": Client.ORDER_TYPE_MARKET,
            "quantity": quantity,
        }
        client = self._get_client()
        if self.testnet:
            return client.create_test_order(**order_params)
        return client.create_order(**order_params)
