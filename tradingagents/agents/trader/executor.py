import re
from typing import Optional, Dict, Any, Tuple

from .binance_client import BinanceTrader


def _is_crypto_symbol(symbol: str) -> bool:
    crypto_symbols = {
        'BTC', 'ETH', 'ADA', 'SOL', 'DOT', 'AVAX', 'MATIC', 'LINK', 'UNI', 'AAVE',
        'XRP', 'LTC', 'BCH', 'EOS', 'TRX', 'XLM', 'VET', 'ALGO', 'ATOM', 'LUNA',
        'NEAR', 'FTM', 'CRO', 'SAND', 'MANA', 'AXS', 'GALA', 'ENJ', 'CHZ', 'BAT',
        'ZEC', 'DASH', 'XMR', 'DOGE', 'SHIB', 'PEPE', 'FLOKI', 'BNB', 'USDT', 'USDC',
        'TON', 'ICP', 'HBAR', 'THETA', 'FIL', 'ETC', 'MKR', 'APT', 'LDO', 'OP',
        'IMX', 'GRT', 'RUNE', 'FLOW', 'EGLD', 'XTZ', 'MINA', 'ROSE', 'KAVA'
    }
    su = symbol.upper()
    if su in crypto_symbols:
        return True
    # Short 2-4 char alphanumerics are often crypto tickers
    return len(su) <= 4 and su.isalnum() and not any(c in su for c in ['.', '-', '_'])


def _parse_decision(text: str) -> str:
    if not text:
        return "HOLD"
    m = re.search(r"FINAL\s+TRANSACTION\s+PROPOSAL:\s*\*\*(BUY|SELL|HOLD)\*\*", text, re.IGNORECASE)
    if m:
        return m.group(1).upper()
    # fallback simple parse
    up = text.upper()
    if " BUY" in up or up.startswith("BUY"):
        return "BUY"
    if " SELL" in up or up.startswith("SELL"):
        return "SELL"
    return "HOLD"


def _parse_tp_sl(text: str) -> Tuple[Optional[float], Optional[float], bool]:
    """Parse TP/SL from text.

    Supports:
    - Percent values (e.g., TP 1.5%, SL 0.8%)
    - Human-formatted absolutes with separators and suffixes (e.g., 109K, 1,250.50, 109.000, 1.2M)

    Returns (tp_value, sl_value, is_percent) where is_percent indicates both values are percents.
    """
    if not text:
        return None, None, False
    import re

    def parse_human_number(num_str: str) -> Optional[float]:
        if not num_str:
            return None
        s = num_str.strip().upper()
        # Strip currency and spaces
        s = re.sub(r"[\s\$€£USDT]+", "", s)
        # Suffix multipliers
        mult = 1.0
        if s.endswith("K"):
            mult, s = 1e3, s[:-1]
        elif s.endswith("M"):
            mult, s = 1e6, s[:-1]
        elif s.endswith("B"):
            mult, s = 1e9, s[:-1]
        elif s.endswith("T"):
            mult, s = 1e12, s[:-1]

        # If both separators present, decide likely decimal separator by last occurrence
        if "," in s and "." in s:
            # Assume thousand-grouping with one of them; if last separator is comma and followed by 2 digits => decimal comma
            last_comma = s.rfind(",")
            last_dot = s.rfind(".")
            if last_comma > last_dot:
                # Prefer comma as decimal if not followed by 3 digits
                frac = s[last_comma + 1 :]
                if len(frac) != 3:
                    s = s.replace(".", "")
                    s = s.replace(",", ".")
                else:
                    # comma as thousand, dot as decimal
                    s = s.replace(",", "")
            else:
                # dot is last
                frac = s[last_dot + 1 :]
                if len(frac) == 3:
                    # treat dot as thousands
                    s = s.replace(".", "")
                    s = s.replace(",", ".")  # any comma likely decimal if present
                else:
                    # dot as decimal, remove commas
                    s = s.replace(",", "")
        elif "." in s:
            # Single dot: if exactly 3 digits after, likely thousand separator
            parts = s.split(".")
            if len(parts) == 2 and len(parts[1]) == 3 and parts[0].isdigit() and parts[1].isdigit():
                s = parts[0] + parts[1]
            else:
                # assume decimal dot; leave as-is
                pass
        elif "," in s:
            # Single comma: decide as thousand vs decimal
            parts = s.split(",")
            if len(parts) == 2 and len(parts[1]) == 3 and parts[0].isdigit() and parts[1].isdigit():
                s = parts[0] + parts[1]
            else:
                # probably decimal comma
                s = s.replace(",", ".")

        try:
            return float(s) * mult
        except Exception:
            return None

    up = text.upper()

    # Percent first
    tp_pct = re.search(r"(?:TP|TAKE\s*PROFIT)[^\d%]*([0-9]+(?:[\.,][0-9]+)?)%", up)
    sl_pct = re.search(r"(?:SL|STOP\s*LOSS)[^\d%]*([0-9]+(?:[\.,][0-9]+)?)%", up)
    if tp_pct or sl_pct:
        tpv = parse_human_number(tp_pct.group(1)) if tp_pct else None
        slv = parse_human_number(slv := sl_pct.group(1)) if sl_pct else None
        return tpv, slv, True

    # Absolutes possibly with K/M/B and locale separators
    tp_abs = re.search(r"(?:TP|TAKE\s*PROFIT)[^\dKMBT%]*([0-9][0-9\.,]*\s*[KMBT]?)", up)
    sl_abs = re.search(r"(?:SL|STOP\s*LOSS)[^\dKMBT%]*([0-9][0-9\.,]*\s*[KMBT]?)", up)
    tpv = parse_human_number(tp_abs.group(1)) if tp_abs else None
    slv = parse_human_number(sl_abs.group(1)) if sl_abs else None
    return tpv, slv, False


def create_trade_executor(config: Dict[str, Any]):
    api_key = config.get("binance_api_key")
    api_secret = config.get("binance_api_secret")
    mode = config.get("trading_mode", "paper")
    quantity = float(config.get("trade_quantity", 0.001))

    binance: Optional[BinanceTrader] = None
    if api_key and api_secret:
        try:
            binance = BinanceTrader(api_key, api_secret, mode)
        except Exception:
            binance = None

    def trade_executor_node(state):
        """Execute trade based on final portfolio/risk decision."""
        final_decision_text = state.get("final_trade_decision", "")
        decision = _parse_decision(final_decision_text)
        tp_val, sl_val, is_percent = _parse_tp_sl(final_decision_text)

        company = state.get("company_of_interest", "").upper()
        symbol = company

        executed = False
        result = None
        error = None

        from tradingagents.utils.trade_log import load_trades, append_trade, close_last_open

        # We always record the decision (BUY/SELL/HOLD), even if no API keys
        recent = load_trades(config, company)
        last_open = next((t for t in reversed(recent) if t.get("status") == "open"), None)

        if decision in {"BUY", "SELL"} and _is_crypto_symbol(company):
            if not symbol.endswith("USDT"):
                symbol = symbol + "USDT"

            if decision == "BUY" and last_open:
                executed = False
                error = "Skipped BUY: open position exists"
            else:
                # Try to execute if keys available; otherwise, just log
                try:
                    if binance:
                        if decision == "BUY":
                            result = binance.execute_market(symbol, decision, quantity)
                            executed = True
                            # Bracket if TP/SL available
                            if tp_val or sl_val:
                                current = binance.get_last_price(symbol)
                                tp_price = None
                                sl_price = None
                                if is_percent:
                                    if tp_val:
                                        tp_price = current * (1 + tp_val / 100.0)
                                    if sl_val:
                                        sl_price = current * (1 - sl_val / 100.0)
                                else:
                                    tp_price = tp_val if tp_val else None
                                    sl_price = sl_val if sl_val else None
                                if tp_price and sl_price:
                                    binance.place_bracket_after_buy(symbol, quantity, tp_price, sl_price)
                        elif decision == "SELL":
                            try:
                                binance.cancel_open_orders(symbol)
                            except Exception:
                                pass
                            sell_qty = float(last_open.get("quantity", quantity)) if last_open else quantity
                            result = binance.execute_market(symbol, decision, sell_qty)
                            executed = True
                    else:
                        # No API — logical execution only
                        executed = False
                except Exception as e:
                    error = str(e)

            # Persist decision
            record = {
                "symbol": symbol,
                "decision": decision,
                "quantity": quantity if decision == "BUY" else (float(last_open.get("quantity", quantity)) if last_open else quantity),
                "take_profit": f"{tp_val}{'%' if is_percent else ''}" if tp_val is not None else "",
                "stop_loss": f"{sl_val}{'%' if is_percent else ''}" if sl_val is not None else "",
                "status": "open" if (decision == "BUY" and not last_open) else ("closed" if (decision == "SELL" and last_open) else ("skipped" if decision == "BUY" and last_open else "closed" if decision == "SELL" and not last_open else "hold")),
                "error": error,
            }
            append_trade(config, company, record)
            if decision == "SELL" and last_open:
                close_last_open(config, company)
        else:
            # HOLD or non-crypto: just log the decision for visibility
            record = {
                "symbol": company,
                "decision": decision,
                "quantity": quantity,
                "take_profit": f"{tp_val}{'%' if is_percent else ''}" if tp_val is not None else "",
                "stop_loss": f"{sl_val}{'%' if is_percent else ''}" if sl_val is not None else "",
                "status": "hold" if decision == "HOLD" else "skipped",
                "error": None,
            }
            append_trade(config, company, record)

        return {
            "trade_execution_result": {
                "attempted": decision in {"BUY", "SELL"},
                "executed": executed,
                "symbol": symbol,
                "side": decision,
                "quantity": quantity,
                "mode": mode,
                "error": error,
                "raw": result,
                "tp": tp_val,
                "sl": sl_val,
                "tp_sl_percent": is_percent,
            }
        }

    return trade_executor_node
