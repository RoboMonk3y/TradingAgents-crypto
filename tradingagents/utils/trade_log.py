import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any


def _log_dir(config: Dict[str, Any], symbol: str) -> Path:
    base = Path(config.get("results_dir", "./results"))
    return base / "trades" / symbol.upper()


def _log_path(config: Dict[str, Any], symbol: str) -> Path:
    return _log_dir(config, symbol) / "trade_log.json"


def load_trades(config: Dict[str, Any], symbol: str, limit: int = 20) -> List[Dict[str, Any]]:
    path = _log_path(config, symbol)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data[-limit:]
        return []
    except Exception:
        return []


def append_trade(config: Dict[str, Any], symbol: str, entry: Dict[str, Any], retention: int = 20) -> List[Dict[str, Any]]:
    dir_path = _log_dir(config, symbol)
    dir_path.mkdir(parents=True, exist_ok=True)
    path = _log_path(config, symbol)

    now_iso = datetime.utcnow().isoformat()
    entry = {"timestamp": now_iso, **entry}

    existing = load_trades(config, symbol, limit=retention)
    existing.append(entry)
    # Ensure retention limit
    data = existing[-retention:]
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data


def recent_trades_snippet(config: Dict[str, Any], symbol: str, limit: int = 20) -> str:
    items = load_trades(config, symbol, limit)
    if not items:
        return "No recent trades recorded."
    lines = ["Recent Trades (last {}):".format(min(limit, len(items)))]
    for t in items[-limit:]:
        ts = t.get("timestamp", "")
        decision = t.get("decision", "")
        tp = t.get("take_profit", "")
        sl = t.get("stop_loss", "")
        status = t.get("status", "")
        qty = t.get("quantity", "")
        lines.append(f"- {ts} | {decision} | TP: {tp} | SL: {sl} | Q: {qty} | {status}")
    return "\n".join(lines)


def close_last_open(config: Dict[str, Any], symbol: str) -> None:
    """Mark the most recent open trade as closed in the log."""
    path = _log_path(config, symbol)
    if not path.exists():
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        for i in range(len(data) - 1, -1, -1):
            if data[i].get("status") == "open":
                data[i]["status"] = "closed"
                break
        path.write_text(json.dumps(data[-20:], indent=2), encoding="utf-8")
    except Exception:
        pass


def list_symbols_with_logs(config: Dict[str, Any]) -> List[str]:
    base = Path(config.get("results_dir", "./results")) / "trades"
    if not base.exists():
        return []
    return sorted([p.name for p in base.iterdir() if p.is_dir()])
