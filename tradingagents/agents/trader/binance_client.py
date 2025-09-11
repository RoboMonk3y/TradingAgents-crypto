"""Binance API helper for executing trades in paper or live modes with basic bracket support."""

from binance.client import Client
from typing import Optional, Dict, Any


class BinanceTrader:
    """Wrapper around the Binance Client to handle live/paper trading and basic bracket (TP/SL)."""

    def __init__(self, api_key: str, api_secret: str, mode: str = "paper") -> None:
        self.testnet = mode.lower() == "paper"
        self.api_key = api_key
        self.api_secret = api_secret
        self._client: Optional[Client] = None
        self._filters: Dict[str, Dict[str, Any]] = {}

    def _get_client(self) -> Client:
        if self._client is None:
            # python-binance uses the correct Spot Testnet base when testnet=True
            self._client = Client(self.api_key, self.api_secret, testnet=self.testnet)
        return self._client

    def _ensure_symbol_filters(self, symbol: str) -> None:
        if symbol in self._filters:
            return
        client = self._get_client()
        info = client.get_symbol_info(symbol)
        if not info:
            self._filters[symbol] = {}
            return
        fs = {}
        for f in info.get("filters", []):
            fs[f["filterType"]] = f
        self._filters[symbol] = fs

    def _round_step(self, symbol: str, qty: float) -> float:
        self._ensure_symbol_filters(symbol)
        step = float(self._filters.get(symbol, {}).get("LOT_SIZE", {}).get("stepSize", 0)) or 0.0
        if step <= 0:
            return float(f"{qty:.6f}")
        precision = max(0, str(step).rstrip('0')[2:].__len__()) if '.' in str(step) else 0
        rounded = (int(qty / step)) * step
        return float(f"{rounded:.{precision}f}")

    def _round_tick(self, symbol: str, price: float) -> float:
        self._ensure_symbol_filters(symbol)
        tick = float(self._filters.get(symbol, {}).get("PRICE_FILTER", {}).get("tickSize", 0)) or 0.0
        if tick <= 0:
            return float(f"{price:.6f}")
        precision = max(0, str(tick).rstrip('0')[2:].__len__()) if '.' in str(tick) else 0
        rounded = (int(price / tick)) * tick
        return float(f"{rounded:.{precision}f}")

    def get_last_price(self, symbol: str) -> float:
        client = self._get_client()
        data = client.get_symbol_ticker(symbol=symbol)
        return float(data.get("price", 0.0)) if data else 0.0

    def cancel_open_orders(self, symbol: str):
        client = self._get_client()
        try:
            return client.cancel_open_orders(symbol=symbol)
        except Exception:
            return None

    def execute_market(self, symbol: str, side: str, quantity: float):
        order_params = {
            "symbol": symbol,
            "side": side.upper(),
            "type": Client.ORDER_TYPE_MARKET,
            "quantity": self._round_step(symbol, quantity),
        }
        client = self._get_client()
        # Spot Testnet often behaves like prod and may not accept create_test_order for MARKET qtys filtered; use create_order
        return client.create_order(**order_params)

    def place_bracket_after_buy(self, symbol: str, quantity: float, tp_price: float, sl_price: float):
        """Place an OCO sell with TP and SL for an existing long position."""
        client = self._get_client()
        qty = self._round_step(symbol, quantity)
        tp = self._round_tick(symbol, tp_price)
        sl_trig = self._round_tick(symbol, sl_price)
        # stopLimit slightly below stopPrice
        sl_limit = self._round_tick(symbol, sl_trig * 0.999)
        try:
            return client.create_oco_order(
                symbol=symbol,
                side=Client.SIDE_SELL,
                quantity=qty,
                price=f"{tp}",
                stopPrice=f"{sl_trig}",
                stopLimitPrice=f"{sl_limit}",
                stopLimitTimeInForce=Client.TIME_IN_FORCE_GTC,
            )
        except Exception as e:
            return {"error": str(e)}
