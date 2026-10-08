"""
analyzer.py
Core digit analysis engine for Deriv digit contracts.
"""

from collections import Counter
from dataclasses import dataclass, field
from typing import List, Optional, Dict


@dataclass
class DigitStats:
    """Holds computed statistics for a window of ticks."""
    total_ticks: int = 0
    digit_freq: Dict[int, int] = field(default_factory=dict)
    even_count: int = 0
    odd_count: int = 0
    over4_count: int = 0   # digits 5-9
    under5_count: int = 0   # digits 0-4
    odd_streak: int = 0
    even_streak: int = 0
    over_streak: int = 0
    under_streak: int = 0
    last_digit: Optional[int] = None

    @property
    def even_pct(self) -> float:
        return (self.even_count / self.total_ticks * 100) if self.total_ticks else 0

    @property
    def odd_pct(self) -> float:
        return (self.odd_count / self.total_ticks * 100) if self.total_ticks else 0

    @property
    def over4_pct(self) -> float:
        return (self.over4_count / self.total_ticks * 100) if self.total_ticks else 0

    @property
    def under5_pct(self) -> float:
        return (self.under5_count / self.total_ticks * 100) if self.total_ticks else 0


@dataclass
class Signal:
    """Represents an analysis signal output."""
    market_type: str = ""
    contract_type: str = ""
    start_stop: str = "Stop"
    entry_point: Optional[str] = None
    reason: str = "No clear signal"


def extract_last_digit(price: float) -> int:
    """
    Extract the last digit from a price.

    E.g. 1234.56 -> 6, 987.03 -> 3, 100.00 -> 0
    """
    # Format to 2 decimal places, take last character
    formatted = f"{price:.2f}"
    return int(formatted[-1])


def compute_stats(prices: List[float]) -> DigitStats:
    """Compute digit statistics from a list of prices."""
    if not prices:
        return DigitStats()

    digits = [extract_last_digit(p) for p in prices]
    total = len(digits)
    freq = Counter(digits)

    even = sum(1 for d in digits if d % 2 == 0)
    odd = total - even
    over4 = sum(1 for d in digits if d >= 5)
    under5 = total - over4

    # Streaks (from the most recent tick backwards)
    def streak(seq, pred):
        s = 0
        for x in reversed(seq):
            if pred(x):
                s += 1
            else:
                break
        return s

    return DigitStats(
        total_ticks=total,
        digit_freq=dict(freq),
        even_count=even,
        odd_count=odd,
        over4_count=over4,
        under5_count=under5,
        odd_streak=streak(digits, lambda d: d % 2 == 1),
        even_streak=streak(digits, lambda d: d % 2 == 0),
        over_streak=streak(digits, lambda d: d >= 5),
        under_streak=streak(digits, lambda d: d <= 4),
        last_digit=digits[-1] if digits else None,
    )


def analyze(
    prices: List[float],
    market_name: str,
    contract_type: str,
    window: int = 100,
    target_digit: int = 7,
) -> Signal:
    """
    Analyze digit statistics and produce a trading signal.

    Args:
        prices: List of historical prices (most recent last).
        market_name: Human-readable market name.
        contract_type: "Even/Odd", "Over/Under", or "Matches/Differs".
        window: Number of recent ticks to analyze.
        target_digit: Target digit for Matches/Differs contracts.

    Returns:
        Signal dataclass with all fields populated.
    """
    recent = prices[-window:] if len(prices) > window else prices
    stats = compute_stats(recent)

    signal = Signal(
        market_type=market_name,
        contract_type=contract_type,
    )

    if stats.total_ticks < 20:
        signal.reason = f"Insufficient data ({stats.total_ticks} ticks, need 20+)"
        return signal

    # --- Even/Odd Logic ---
    if contract_type == "Even/Odd":
        if stats.odd_streak >= 3 and stats.even_pct < 45:
            signal.start_stop = "Start"
            signal.entry_point = "Even"
            signal.reason = (
                f"Odd streak {stats.odd_streak}, "
                f"even only {stats.even_pct:.1f}% in last {stats.total_ticks}"
            )
        elif stats.even_streak >= 3 and stats.odd_pct < 45:
            signal.start_stop = "Start"
            signal.entry_point = "Odd"
            signal.reason = (
                f"Even streak {stats.even_streak}, "
                f"odd only {stats.odd_pct:.1f}% in last {stats.total_ticks}"
            )
        else:
            signal.reason = (
                f"No edge. Even {stats.even_pct:.1f}% / "
                f"Odd {stats.odd_pct:.1f}% | "
                f"Odd streak {stats.odd_streak}, Even streak {stats.even_streak}"
            )

    # --- Over/Under Logic ---
    elif contract_type == "Over/Under":
        if stats.over4_pct > 60:
            signal.start_stop = "Start"
            signal.entry_point = "Over 4"
            signal.reason = (
                f"Over 4 frequency {stats.over4_pct:.1f}% "
                f"in last {stats.total_ticks} ticks"
            )
        elif stats.under5_pct > 60:
            signal.start_stop = "Start"
            signal.entry_point = "Under 5"
            signal.reason = (
                f"Under 5 frequency {stats.under5_pct:.1f}% "
                f"in last {stats.total_ticks} ticks"
            )
        else:
            signal.reason = (
                f"No edge. Over 4 {stats.over4_pct:.1f}% / "
                f"Under 5 {stats.under5_pct:.1f}%"
            )

    # --- Matches/Differs Logic ---
    elif contract_type == "Matches/Differs":
        freq = stats.digit_freq
        pct = (freq.get(target_digit, 0) / stats.total_ticks) * 100

        if pct < 5:
            signal.start_stop = "Start"
            signal.entry_point = f"Differs {target_digit}"
            signal.reason = (
                f"Digit {target_digit} frequency {pct:.1f}% < 5% "
                f"in last {stats.total_ticks} ticks"
            )
        elif pct > 15:
            signal.start_stop = "Start"
            signal.entry_point = f"Matches {target_digit}"
            signal.reason = (
                f"Digit {target_digit} frequency {pct:.1f}% > 15% "
                f"in last {stats.total_ticks} ticks"
            )
        else:
            signal.reason = (
                f"No edge. Digit {target_digit} frequency {pct:.1f}%"
            )

    return signal


def format_signal(signal: Signal) -> str:
    """Format a Signal into the user-requested display format."""
    lines = [
        f"Market type        : {signal.market_type}",
        f"Contract type      : {signal.contract_type}",
        f"Start/stop button  : {signal.start_stop}",
        f"Entry point        : {signal.entry_point or '—'}",
        f"Reason             : {signal.reason}",
    ]
    return "\n".join(lines)
