"""
main.py
Deriv Digit Analyzer — CLI application.

Usage:
    python main.py --market "Volatility 100 (1s) Index" --contract "Even/Odd"
    python main.py --market "Volatility 75 Index" --contract "Over/Under"
    python main.py --market "Volatility 100 Index" --contract "Matches/Differs" --digit 7
"""

import argparse
import asyncio
import logging
import sys
from datetime import datetime

from deriv_client import DerivClient, SYMBOLS
from analyzer import analyze, format_signal, compute_stats

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Deriv Digit Analyzer — Real-time digit contract analysis"
    )
    parser.add_argument(
        "--market",
        type=str,
        default="Volatility 100 (1s) Index",
        choices=list(SYMBOLS.keys()),
        help="Deriv synthetic market to analyze",
    )
    parser.add_argument(
        "--contract",
        type=str,
        default="Even/Odd",
        choices=["Even/Odd", "Over/Under", "Matches/Differs"],
        help="Digit contract type",
    )
    parser.add_argument(
        "--digit",
        type=int,
        default=7,
        choices=range(10),
        help="Target digit for Matches/Differs (0-9)",
    )
    parser.add_argument(
        "--window",
        type=int,
        default=100,
        help="Number of recent ticks to analyze (default: 100)",
    )
    parser.add_argument(
        "--history",
        type=int,
        default=500,
        help="Number of historical ticks to fetch on startup (default: 500)",
    )
    parser.add_argument(
        "--token",
        type=str,
        default=None,
        help="Deriv API token (optional, for authorized data)",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=5.0,
        help="Seconds between analysis prints (default: 5)",
    )
    return parser.parse_args()


async def run_analyzer(args):
    """Main async loop: fetch history, stream ticks, analyze."""
    symbol = SYMBOLS[args.market]
    client = DerivClient(api_token=args.token)

    await client.connect()

    # 1. Fetch historical ticks
    logger.info(f"Fetching {args.history} historical ticks for {args.market}...")
    history = await client.get_ticks_history(symbol, count=args.history)
    prices = [t["quote"] for t in history]
    logger.info(f"Loaded {len(prices)} ticks.")

    # 2. Print initial analysis
    print("\n" + "=" * 55)
    print(f"  DERIV DIGIT ANALYZER — {args.market}")
    print("=" * 55)
    print_analysis(prices, args)

    # 3. Stream live ticks
    logger.info("Streaming live ticks... Press Ctrl+C to stop.\n")
    last_print = 0.0

    try:
        async for tick in client.stream_ticks(symbol):
            prices.append(tick["quote"])

            # Keep buffer manageable
            if len(prices) > args.history:
                prices = prices[-args.history:]

            now = asyncio.get_event_loop().time()
            if now - last_print >= args.interval:
                last_print = now
                print_analysis(prices, args)
                print(f"  Last tick: {tick['quote']:.2f}  |  "
                      f"Time: {datetime.fromtimestamp(tick['epoch']).strftime('%H:%M:%S')}")
                print("-" * 55)

    except KeyboardInterrupt:
        logger.info("Stopping analyzer...")
    finally:
        await client.close()


def print_analysis(prices, args):
    """Compute and print the analysis in the requested format."""
    signal = analyze(
        prices=prices,
        market_name=args.market,
        contract_type=args.contract,
        window=args.window,
        target_digit=args.digit,
    )
    print(format_signal(signal))
    print()

    # Also print digit frequency table for reference
    stats = compute_stats(prices[-args.window:])
    print("  Digit Frequency (last {} ticks):".format(stats.total_ticks))
    for d in range(10):
        count = stats.digit_freq.get(d, 0)
        pct = (count / stats.total_ticks * 100) if stats.total_ticks else 0
        bar = "█" * int(pct / 2)
        marker = " *" if d == stats.last_digit else ""
        print(f"    {d}: {count:4d}  ({pct:5.1f}%)  {bar}{marker}")
    print()


def main():
    args = parse_args()
    try:
        asyncio.run(run_analyzer(args))
    except KeyboardInterrupt:
        print("\nGoodbye.")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
