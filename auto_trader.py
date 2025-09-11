import argparse
import os
import time
from datetime import datetime

from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG


def run_loop(ticker: str, interval_secs: int, analysts, research_depth: int, provider: str, backend_url: str, api_key: str):
    print(f"[AUTO] Starting auto-trader for {ticker} every {interval_secs}s")

    base_config = DEFAULT_CONFIG.copy()
    base_config.update({
        "llm_provider": provider,
        "backend_url": backend_url,
        "api_key": api_key,
        "quick_think_llm": base_config.get("quick_think_llm"),
        "deep_think_llm": base_config.get("deep_think_llm"),
        "research_depth": research_depth,
    })

    graph = TradingAgentsGraph(selected_analysts=analysts, debug=False, config=base_config)

    while True:
        try:
            curr_date = datetime.utcnow().strftime("%Y-%m-%d")
            print(f"[AUTO] {datetime.utcnow().isoformat()} - Running analysis for {ticker}")
            final_state, processed = graph.propagate(ticker, curr_date)
            print(f"[AUTO] Completed. Decision: {final_state.get('final_trade_decision','')[:120]}")
        except Exception as e:
            print(f"[AUTO] Error: {e}")
        time.sleep(interval_secs)


def main():
    parser = argparse.ArgumentParser(description="Run auto trader loop")
    parser.add_argument("--ticker", default=os.getenv("AUTO_TICKER", "BTC"))
    parser.add_argument("--interval", type=int, default=int(os.getenv("AUTO_INTERVAL", "1800")))
    parser.add_argument("--provider", default=os.getenv("LLM_PROVIDER", DEFAULT_CONFIG.get("llm_provider", "openai")))
    parser.add_argument("--backend-url", default=os.getenv("LLM_BACKEND_URL", DEFAULT_CONFIG.get("backend_url", "https://api.openai.com/v1")))
    parser.add_argument("--api-key", default=os.getenv("OPENAI_API_KEY", os.getenv("API_KEY", "")))
    parser.add_argument("--research-depth", type=int, default=int(os.getenv("RESEARCH_DEPTH", str(DEFAULT_CONFIG.get("max_debate_rounds", 1)))))
    parser.add_argument("--analysts", default=os.getenv("ANALYSTS", "market,social,news,fundamentals"))

    args = parser.parse_args()

    analysts = [a.strip() for a in args.analysts.split(",") if a.strip()]
    run_loop(
        ticker=args.ticker,
        interval_secs=args.interval,
        analysts=analysts,
        research_depth=args.research_depth,
        provider=args.provider,
        backend_url=args.backend_url,
        api_key=args.api_key,
    )


if __name__ == "__main__":
    main()

