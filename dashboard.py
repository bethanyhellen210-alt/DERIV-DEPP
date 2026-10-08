"""
dashboard.py
Streamlit web dashboard for Deriv digit analysis.
Run with: streamlit run dashboard.py
"""

import asyncio
import time
from datetime import datetime

import streamlit as st
import pandas as pd

from deriv_client import DerivClient, SYMBOLS
from analyzer import analyze, compute_stats, extract_last_digit

st.set_page_config(page_title="Deriv Digit Analyzer", layout="wide")
st.title("📊 Deriv Digit Analyzer")

# --- Sidebar Controls ---
with st.sidebar:
    st.header("Settings")
    market = st.selectbox("Market", list(SYMBOLS.keys()), index=9)
    contract = st.selectbox(
        "Contract Type",
        ["Even/Odd", "Over/Under", "Matches/Differs"]
    )
    target_digit = st.slider("Target Digit (Matches/Differs)", 0, 9, 7)
    window = st.slider("Analysis Window (ticks)", 20, 500, 100)
    history_count = st.slider("Historical Ticks", 100, 2000, 500)
    interval = st.slider("Update Interval (sec)", 2, 30, 5)

    start_btn = st.button("🚀 Start Analysis", use_container_width=True)
    stop_btn = st.button("⏹ Stop", use_container_width=True)


# --- Session State ---
if "running" not in st.session_state:
    st.session_state.running = False
if "prices" not in st.session_state:
    st.session_state.prices = []


async def fetch_and_update():
    """Fetch history and stream ticks, updating the UI."""
    symbol = SYMBOLS[market]
    client = DerivClient()
    await client.connect()

    # Fetch history
    history = await client.get_ticks_history(symbol, count=history_count)
    st.session_state.prices = [t["quote"] for t in history]

    placeholder = st.empty()

    try:
        async for tick in client.stream_ticks(symbol):
            if not st.session_state.running:
                break

            st.session_state.prices.append(tick["quote"])
            if len(st.session_state.prices) > history_count:
                st.session_state.prices = st.session_state.prices[-history_count:]

            # Update UI
            with placeholder.container():
                render_dashboard(
                    st.session_state.prices,
                    market, contract, target_digit, window, tick
                )
            await asyncio.sleep(interval)

    finally:
        await client.close()


def render_dashboard(prices, market, contract, target_digit, window, last_tick):
    """Render the analysis dashboard."""
    signal = analyze(prices, market, contract, window, target_digit)
    stats = compute_stats(prices[-window:])

    # --- Signal Card ---
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Market", signal.market_type)
    with col2:
        color = "🟢" if signal.start_stop == "Start" else "🔴"
        st.metric("Signal", f"{color} {signal.start_stop}")
    with col3:
        st.metric("Entry Point", signal.entry_point or "—")

    st.info(f"**Reason:** {signal.reason}")

    # --- Digit Frequency Chart ---
    st.subheader("Digit Frequency")
    df = pd.DataFrame({
        "Digit": list(range(10)),
        "Count": [stats.digit_freq.get(d, 0) for d in range(10)],
    })
    df["Percentage"] = (df["Count"] / stats.total_ticks * 100).round(1)
    st.bar_chart(df.set_index("Digit")["Count"])

    # --- Stats Table ---
    col_a, col_b, col_c, col_d = st.columns(4)
    col_a.metric("Even %", f"{stats.even_pct:.1f}%")
    col_b.metric("Odd %", f"{stats.odd_pct:.1f}%")
    col_c.metric("Over 4 %", f"{stats.over4_pct:.1f}%")
    col_d.metric("Under 5 %", f"{stats.under5_pct:.1f}%")

    st.caption(
        f"Last tick: {last_tick['quote']:.2f} | "
        f"Last digit: {stats.last_digit} | "
        f"Ticks analyzed: {stats.total_ticks} | "
        f"Time: {datetime.fromtimestamp(last_tick['epoch']).strftime('%H:%M:%S')}"
    )


# --- Main Logic ---
if start_btn:
    st.session_state.running = True
    asyncio.run(fetch_and_update())

if stop_btn:
    st.session_state.running = False

if not st.session_state.running and st.session_state.prices:
    render_dashboard(
        st.session_state.prices, market, contract,
        target_digit, window,
        {"quote": st.session_state.prices[-1], "epoch": time.time()}
  )
