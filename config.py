"""
config.py
Central configuration: branding, access keys, defaults.
"""

# --- Access Keys ---
# Add or remove keys here. Each key is a string.
# In production, store these in a database or env variable.
VALID_KEYS = {
    "DERIV-2026-ALPHA":  {"plan": "Pro",    "uses": 9999},
    "DERIV-2026-BETA":   {"plan": "Starter","uses": 500},
    "DERIV-2026-GUEST":  {"plan": "Demo",   "uses": 50},
    "MASTER-KEY-XYZ":    {"plan": "Admin",  "uses": 99999},
}

# --- Branding ---
APP_NAME = "DigitEdge"
APP_TAGLINE = "Statistical Digit Analysis for Deriv Synthetic Indices"
APP_LOGO_EMOJI = "📊"

# --- Defaults ---
DEFAULT_MARKET = "Volatility 100 (1s) Index"
DEFAULT_CONTRACT = "Even/Odd"
DEFAULT_WINDOW = 100
DEFAULT_HISTORY = 500
DEFAULT_INTERVAL = 5
