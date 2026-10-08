"""
app.py
DigitEdge — Landing page + access key gate + analyzer dashboard.

Run with:
    streamlit run app.py
"""

import asyncio
import time
from datetime import datetime

import streamlit as st
import pandas as pd

from config import (
    VALID_KEYS, APP_NAME, APP_TAGLINE, APP_LOGO_EMOJI,
    DEFAULT_MARKET, DEFAULT_CONTRACT, DEFAULT_WINDOW,
    DEFAULT_HISTORY, DEFAULT_INTERVAL,
)
from deriv_client import DerivClient, SYMBOLS
from analyzer import analyze, compute_stats


# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title=f"{APP_NAME} — Deriv Digit Analyzer",
    page_icon=APP_LOGO_EMOJI,
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ============================================================
# GLOBAL CSS
# ============================================================
def inject_css():
    st.markdown("""
    <style>
    /* ---------- Global ---------- */
    .stApp {
        background: radial-gradient(circle at 20% 0%, #0f1a2e 0%, #070b14 55%, #03050a 100%);
        color: #e6edf7;
    }
    section.main > div { padding-top: 1rem; }
    footer { visibility: hidden; }
    #MainMenu { visibility: hidden; }

    /* ---------- Landing Hero ---------- */
    .hero-wrap {
        max-width: 1100px;
        margin: 0 auto;
        padding: 3rem 1rem 1rem 1rem;
        text-align: center;
    }
    .badge {
        display: inline-block;
        padding: 6px 14px;
        border-radius: 999px;
        background: rgba(0, 255, 200, 0.08);
        border: 1px solid rgba(0, 255, 200, 0.35);
        color: #4ff0c4;
        font-size: 0.78rem;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        font-weight: 600;
        margin-bottom: 1.2rem;
    }
    .hero-title {
        font-size: 3.4rem;
        font-weight: 800;
        line-height: 1.1;
        margin: 0 0 1rem 0;
        background: linear-gradient(90deg, #ffffff 0%, #7ad7ff 50%, #4ff0c4 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    .hero-sub {
        font-size: 1.15rem;
        color: #9fb0c8;
        max-width: 720px;
        margin: 0 auto 2rem auto;
        line-height: 1.6;
    }

    /* ---------- Feature Grid ---------- */
    .feature-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
        gap: 1rem;
        max-width: 1100px;
        margin: 2rem auto 3rem auto;
        padding: 0 1rem;
    }
    .feature-card {
        background: linear-gradient(180deg, rgba(255,255,255,0.04) 0%, rgba(255,255,255,0.01) 100%);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 16px;
        padding: 1.4rem 1.3rem;
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .feature-card:hover {
        transform: translateY(-3px);
        border-color: rgba(79, 240, 196, 0.45);
    }
    .feature-icon {
        font-size: 1.8rem;
        margin-bottom: 0.6rem;
    }
    .feature-title {
        font-size: 1.05rem;
        font-weight: 700;
        color: #e6edf7;
        margin-bottom: 0.4rem;
    }
    .feature-desc {
        font-size: 0.9rem;
        color: #8ea1bd;
        line-height: 1.5;
    }

    /* ---------- Key Gate ---------- */
    .gate-wrap {
        max-width: 460px;
        margin: 1.5rem auto 4rem auto;
        background: linear-gradient(180deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.015) 100%);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 20px;
        padding: 2rem 2rem 1.6rem 2rem;
        box-shadow: 0 20px 60px rgba(0,0,0,0.5);
    }
    .gate-title {
        font-size: 1.35rem;
        font-weight: 700;
        margin: 0 0 0.35rem 0;
        text-align: center;
        color: #ffffff;
    }
    .gate-sub {
        font-size: 0.88rem;
        color: #8ea1bd;
        text-align: center;
        margin-bottom: 1.2rem;
    }

    /* ---------- Streamlit input tweaks ---------- */
    .stTextInput > div > div > input {
        background: rgba(0,0,0,0.35) !important;
        border: 1px solid rgba(255,255,255,0.15) !important;
        color: #e6edf7 !important;
        border-radius: 10px !important;
        padding: 0.7rem 0.9rem !important;
        font-size: 1rem !important;
        letter-spacing: 0.05em;
        text-align: center;
    }
    .stTextInput > div > div > input:focus {
        border-color: #4ff0c4 !important;
        box-shadow: 0 0 0 3px rgba(79, 240, 196, 0.15) !important;
    }

    /* ---------- Buttons ---------- */
    .stButton > button {
        width: 100%;
        background: linear-gradient(90deg, #4ff0c4 0%, #38b6ff 100%);
        color: #041014;
        font-weight: 700;
        border: none;
        border-radius: 10px;
        padding: 0.7rem 1rem;
        font-size: 1rem;
        letter-spacing: 0.03em;
        transition: filter 0.2s ease, transform 0.2s ease;
    }
    .stButton > button:hover {
        filter: brightness(1.1);
        transform: translateY(-1px);
        color: #041014;
    }

    /* ---------- Dashboard ---------- */
    .dash-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        border-bottom: 1px solid rgba(255,255,255,0.08);
        padding-bottom: 1rem;
        margin-bottom: 1.5rem;
    }
    .dash-title {
        font-size: 1.5rem;
        font-weight: 800;
        background: linear-gradient(90deg, #ffffff, #7ad7ff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .signal-card {
        border-radius: 16px;
        padding: 1.4rem 1.6rem;
        border: 1px solid rgba(255,255,255,0.1);
        background: linear-gradient(180deg, rgba(255,255,255,0.05), rgba(255,255,255,0.01));
    }
    .signal-start { border-color: rgba(79, 240, 196, 0.6); box-shadow: 0 0 30px rgba(79,240,196,0.15); }
    .signal-stop  { border-color: rgba(255, 90, 120, 0.5); }
    .signal-label { font-size: 0.75rem; letter-spacing: 0.1em; text-transform: uppercase; color: #8ea1bd; }
    .signal-value { font-size: 1.6rem; font-weight: 800; margin-top: 0.2rem; }
    .signal-green { color: #4ff0c4; }
    .signal-red   { color: #ff5a78; }
    .signal-neutral { color: #7ad7ff; }
    .reason-box {
        margin-top: 1rem;
        padding: 0.9rem 1.1rem;
        border-radius: 12px;
        background: rgba(122, 215, 255, 0.07);
        border: 1px solid rgba(122, 215, 255, 0.2);
        color: #c8d8ee;
        font-size: 0.95rem;
        line-height: 1.5;
    }
    .footnote {
        text-align: center;
        color: #64748b;
        font-size: 0.8rem;
        margin: 3rem 0 1rem 0;
        line-height: 1.6;
    }
    .locked-msg {
        text-align: center;
        color: #ff5a78;
        font-size: 0.9rem;
        margin-top: 0.6rem;
    }
    </style>
    """, unsafe_allow_html=True)


inject_css()


# ============================================================
# SESSION STATE
# ============================================================
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user_plan" not in st.session_state:
    st.session_state.user_plan = None
if "user_key" not in st.session_state:
    st.session_state.user_key = None
if "running" not in st.session_state:
    st.session_state.running = False
if "prices" not in st.session_state:
    st.session_state.prices = []


# ============================================================
# LANDING PAGE
# ============================================================
def render_landing():
    st.markdown(f"""
    <div class="hero-wrap">
        <div class="badge">● Live Deriv Synthetic Indices</div>
        <div class="hero-title">{APP_LOGO_EMOJI} {APP_NAME}<br/>Analyze. Signal. Decide.</div>
        <div class="hero-sub">
            {APP_TAGLINE}. Real-time digit frequency, streak detection,
            even/odd bias, over/under pressure, and match/differ edge — all in one dashboard.
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="feature-grid">
        <div class="feature-card">
            <div class="feature-icon">⚡</div>
            <div class="feature-title">Live Tick Stream</div>
            <div class="feature-desc">Sub-second updates straight from Deriv's WebSocket API. No lag, no refresh.</div>
        </div>
        <div class="feature-card">
            <div class="feature-icon">🔢</div>
            <div class="feature-title">Digit Frequency Engine</div>
            <div class="feature-desc">Full 0–9 histogram with hot/cold detection over a rolling window you control.</div>
        </div>
        <div class="feature-card">
            <div class="feature-icon">🎯</div>
            <div class="feature-title">Signal Generator</div>
            <div class="feature-desc">Even/Odd, Over/Under, and Matches/Differs signals with statistical justification.</div>
        </div>
        <div class="feature-card">
            <div class="feature-icon">🧠</div>
            <div class="feature-title">Reason Transparency</div>
            <div class="feature-desc">Every signal ships with the exact frequency and streak numbers behind it.</div>
        </div>
        <div class="feature-card">
            <div class="feature-icon">📈</div>
            <div class="feature-title">Multi-Market</div>
            <div class="feature-desc">Switch between Volatility 10, 25, 50, 75, 100 and their 1-second variants.</div>
        </div>
        <div class="feature-card">
            <div class="feature-icon">🔐</div>
            <div class="feature-title">Key-Protected Access</div>
            <div class="feature-desc">Private build. Only authorized keys can unlock the dashboard.</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # --- Key Gate ---
    st.markdown("""
    <div class="gate-wrap">
        <div class="gate-title">🔑 Enter Access Key</div>
        <div class="gate-sub">Paste your key below to unlock the analyzer.</div>
    """, unsafe_allow_html=True)

    with st.form("key_form", clear_on_submit=False):
        key_input = st.text_input(
            "Access key",
            placeholder="DERIV-XXXX-XXXX",
            label_visibility="collapsed",
        )
        submitted = st.form_submit_button("Unlock Analyzer →")

    if submitted:
        cleaned = key_input.strip().upper()
        if cleaned in VALID_KEYS:
            st.session_state.authenticated = True
            st.session_state.user_key = cleaned
            st.session_state.user_plan = VALID_KEYS[cleaned]["plan"]
            st.success(f"✅ Access granted — {st.session_state.user_plan} plan")
            time.sleep(0.7)
            st.rerun()
        else:
            st.markdown(
                '<div class="locked-msg">❌ Invalid key. Please check and try again.</div>',
                unsafe_allow_html=True,
            )

    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown(
        '<div class="footnote">DigitEdge is an educational analysis tool. '
        'Deriv synthetic indices are random — no signal guarantees profit. '
        'Trade responsibly.</div>',
        unsafe_allow_html=True,
    )


# ============================================================
# DASHBOARD
# ============================================================
def render_dashboard():
    # --- Header ---
    col_h1, col_h2 = st.columns([3, 1])
    with col_h1:
        st.markdown(
            f'<div class="dash-title">{APP_LOGO_EMOJI} {APP_NAME} — Analyzer</div>',
            unsafe_allow_html=True,
        )
    with col_h2:
        st.caption(f"Plan: **{st.session_state.user_plan}**")
        if st.button("🚪 Logout"):
            st.session_state.authenticated = False
            st.session_state.running = False
            st.session_state.prices = []
            st.rerun()

    st.markdown("---")

    # --- Sidebar controls ---
    with st.sidebar:
        st.header("⚙️ Controls")
        market = st.selectbox(
            "Market",
            list(SYMBOLS.keys()),
            index=list(SYMBOLS.keys()).index(DEFAULT_MARKET),
        )
        contract = st.selectbox(
            "Contract Type",
            ["Even/Odd", "Over/Under", "Matches/Differs"],
            index=0,
        )
        target_digit = st.slider("Target Digit (Matches/Differs)", 0, 9, 7)
        window = st.slider("Analysis Window (ticks)", 20, 500, DEFAULT_WINDOW)
        history_count = st.slider("Historical Ticks", 100, 2000, DEFAULT_HISTORY)
        interval = st.slider("Update Interval (sec)", 2, 30, DEFAULT_INTERVAL)

        st.markdown("---")
        col_a, col_b = st.columns(2)
        with col_a:
            start_btn = st.button("▶ Start")
        with col_b:
            stop_btn = st.button("⏹ Stop")

        st.markdown("---")
        st.caption(
            "⚠️ Synthetic indices are random. "
            "Signals are statistical, not predictive."
        )

    # --- Buttons ---
    if start_btn:
        st.session_state.running = True
    if stop_btn:
        st.session_state.running = False

    # --- Main panel ---
    placeholder = st.empty()

    if st.session_state.running:
        try:
            asyncio.run(_stream_loop(
                placeholder, market, contract, target_digit,
                window, history_count, interval
            ))
        except Exception as e:
            st.error(f"Connection error: {e}")
            st.session_state.running = False
    else:
        with placeholder.container():
            st.info("👈 Configure your market and click **Start** in the sidebar to begin analysis.")


async def _stream_loop(placeholder, market, contract, target_digit,
                       window, history_count, interval):
    """Async streaming loop that updates the dashboard placeholder."""
    symbol = SYMBOLS[market]
    client = DerivClient()
    await client.connect()

    # Initial history
    with st.spinner("Fetching historical ticks..."):
        history = await client.get_ticks_history(symbol, count=history_count)
    st.session_state.prices = [t["quote"] for t in history]

    try:
        async for tick in client.stream_ticks(symbol):
            if not st.session_state.running:
                break

            st.session_state.prices.append(tick["quote"])
            if len(st.session_state.prices) > history_count:
                st.session_state.prices = st.session_state.prices[-history_count:]

            with placeholder.container():
                _render_analysis(
                    st.session_state.prices,
                    market, contract, target_digit, window, tick,
                )

            await asyncio.sleep(interval)
    finally:
        await client.close()


def _render_analysis(prices, market, contract, target_digit, window, last_tick):
    """Render signal card + frequency chart + stats."""
    signal = analyze(prices, market, contract, window, target_digit)
    stats = compute_stats(prices[-window:])

    # --- Signal Card ---
    is_start = signal.start_stop == "Start"
    card_class = "signal-start" if is_start else "signal-stop"
    value_class = "signal-green" if is_start else "signal-red"

    st.markdown(f"""
    <div class="signal-card {card_class}">
        <div style="display:flex; gap:2rem; flex-wrap:wrap;">
            <div style="flex:1; min-width:180px;">
                <div class="signal-label">Market Type</div>
                <div class="signal-value signal-neutral">{signal.market_type}</div>
            </div>
            <div style="flex:1; min-width:150px;">
                <div class="signal-label">Contract Type</div>
                <div class="signal-value signal-neutral">{signal.contract_type}</div>
            </div>
            <div style="flex:1; min-width:130px;">
                <div class="signal-label">Start / Stop</div>
                <div class="signal-value {value_class}">{'🟢' if is_start else '🔴'} {signal.start_stop}</div>
            </div>
            <div style="flex:1; min-width:150px;">
                <div class="signal-label">Entry Point</div>
                <div class="signal-value signal-neutral">{signal.entry_point or '—'}</div>
            </div>
        </div>
        <div class="reason-box"><b>Reason:</b> {signal.reason}</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br/>", unsafe_allow_html=True)

    # --- Frequency + stats ---
    col_chart, col_stats = st.columns([2, 1])

    with col_chart:
        st.subheader("Digit Frequency")
        df = pd.DataFrame({
            "Digit": list(range(10)),
            "Count": [stats.digit_freq.get(d, 0) for d in range(10)],
        })
        df["Percentage"] = (df["Count"] / max(stats.total_ticks, 1) * 100).round(1)
        st.bar_chart(df.set_index("Digit")["Count"], height=320)

    with col_stats:
        st.subheader("Quick Stats")
        st.metric("Ticks Analyzed", stats.total_ticks)
        st.metric("Even %", f"{stats.even_pct:.1f}%")
        st.metric("Odd %", f"{stats.odd_pct:.1f}%")
        st.metric("Over 4 %", f"{stats.over4_pct:.1f}%")
        st.metric("Under 5 %", f"{stats.under5_pct:.1f}%")

    # --- Streaks ---
    st.markdown("#### Streaks")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Odd Streak", stats.odd_streak)
    c2.metric("Even Streak", stats.even_streak)
    c3.metric("Over 4 Streak", stats.over_streak)
    c4.metric("Under 5 Streak", stats.under_streak)

    # --- Last tick ---
    st.caption(
        f"Last tick: **{last_tick['quote']:.2f}** | "
        f"Last digit: **{stats.last_digit}** | "
        f"Time: **{datetime.fromtimestamp(last_tick['epoch']).strftime('%H:%M:%S')}**"
    )


# ============================================================
# ROUTER
# ============================================================
if not st.session_state.authenticated:
    render_landing()
else:
    render_dashboard()
