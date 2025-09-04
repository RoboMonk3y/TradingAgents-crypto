from tradingagents.agents.trader.binance_client import BinanceTrader


def test_binance_trader_modes():
    paper = BinanceTrader('k', 's', mode='paper')
    assert paper.testnet is True
    live = BinanceTrader('k', 's', mode='live')
    assert live.testnet is False
