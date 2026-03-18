"""
₿ Binance Futures Testnet — Trading Dashboard
A premium Streamlit-based trading terminal.
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import time
import hmac
import hashlib
import requests
import os
import json
from datetime import datetime, timedelta
from urllib.parse import urlencode
from dotenv import load_dotenv

# ── Load env ──
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

API_KEY = os.environ.get("BINANCE_API_KEY", "")
API_SECRET = os.environ.get("BINANCE_API_SECRET", "")
BASE_URL = os.environ.get("BINANCE_BASE_URL", "https://testnet.binancefuture.com")

SUPPORTED_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "DOGEUSDT",
    "SOLUSDT", "ADAUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT",
    "MATICUSDT", "LTCUSDT", "TRXUSDT", "UNIUSDT", "ATOMUSDT",
]

SYMBOL_ICONS = {
    "BTCUSDT": "₿", "ETHUSDT": "⟠", "BNBUSDT": "◆", "XRPUSDT": "✕",
    "DOGEUSDT": "Ð", "SOLUSDT": "◎", "ADAUSDT": "₳", "AVAXUSDT": "▲",
    "DOTUSDT": "●", "LINKUSDT": "⬡", "MATICUSDT": "⬢", "LTCUSDT": "Ł",
    "TRXUSDT": "◈", "UNIUSDT": "🦄", "ATOMUSDT": "⚛",
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# API Helpers
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _sign(params: dict) -> dict:
    """Add timestamp and HMAC-SHA256 signature to params."""
    params["timestamp"] = int(time.time() * 1000)
    qs = urlencode(params)
    sig = hmac.new(API_SECRET.encode(), qs.encode(), hashlib.sha256).hexdigest()
    params["signature"] = sig
    return params


def _headers():
    return {"X-MBX-APIKEY": API_KEY}


def api_get(endpoint, params=None, signed=False):
    """Make a GET request to the Binance Futures API."""
    params = params or {}
    if signed:
        params = _sign(params)
    try:
        r = requests.get(f"{BASE_URL}{endpoint}", params=params, headers=_headers(), timeout=15)
        if r.status_code == 200:
            return r.json()
        return {"error": True, "code": r.status_code, "msg": r.text}
    except Exception as e:
        return {"error": True, "msg": str(e)}


def api_post(endpoint, params=None):
    """Make a signed POST request to the Binance Futures API."""
    params = params or {}
    params = _sign(params)
    try:
        r = requests.post(f"{BASE_URL}{endpoint}", params=params, headers=_headers(), timeout=15)
        data = r.json()
        if r.status_code != 200:
            data["error"] = True
        return data
    except Exception as e:
        return {"error": True, "msg": str(e)}


def api_delete(endpoint, params=None):
    """Make a signed DELETE request to the Binance Futures API."""
    params = params or {}
    params = _sign(params)
    try:
        r = requests.delete(f"{BASE_URL}{endpoint}", params=params, headers=_headers(), timeout=15)
        data = r.json()
        if r.status_code != 200:
            data["error"] = True
        return data
    except Exception as e:
        return {"error": True, "msg": str(e)}


@st.cache_data(ttl=5)
def get_price(symbol):
    return api_get("/fapi/v1/ticker/price", {"symbol": symbol})


@st.cache_data(ttl=10)
def get_24h_stats(symbol):
    return api_get("/fapi/v1/ticker/24hr", {"symbol": symbol})


@st.cache_data(ttl=30)
def get_klines(symbol, interval="1h", limit=100):
    data = api_get("/fapi/v1/klines", {"symbol": symbol, "interval": interval, "limit": limit})
    if isinstance(data, list):
        df = pd.DataFrame(data, columns=[
            "open_time", "open", "high", "low", "close", "volume",
            "close_time", "quote_vol", "trades", "buy_base_vol",
            "buy_quote_vol", "ignore"
        ])
        df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = df[col].astype(float)
        return df
    return pd.DataFrame()


def get_account():
    return api_get("/fapi/v2/account", signed=True)


def get_open_orders(symbol=None):
    params = {}
    if symbol:
        params["symbol"] = symbol
    return api_get("/fapi/v1/openOrders", params=params, signed=True)


def place_order(symbol, side, order_type, quantity, price=None, stop_price=None, tif="GTC"):
    params = {"symbol": symbol, "side": side, "type": order_type, "quantity": quantity}
    if order_type == "LIMIT":
        params["price"] = price
        params["timeInForce"] = tif
    elif order_type == "STOP":
        params["price"] = price
        params["stopPrice"] = stop_price
        params["timeInForce"] = tif
    return api_post("/fapi/v1/order", params)


def cancel_order(symbol, order_id):
    return api_delete("/fapi/v1/order", {"symbol": symbol, "orderId": order_id})


def get_all_prices():
    data = api_get("/fapi/v1/ticker/price")
    if isinstance(data, list):
        return {d["symbol"]: float(d["price"]) for d in data if d["symbol"] in SUPPORTED_SYMBOLS}
    return {}


@st.cache_data(ttl=10)
def get_recent_trades(symbol, limit=20):
    return api_get("/fapi/v1/trades", {"symbol": symbol, "limit": limit})


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Page Config & Custom CSS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

st.set_page_config(
    page_title="₿ Futures Trading Terminal",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

    /* ── Global ── */
    .stApp {
        font-family: 'Inter', sans-serif;
    }
    
    /* ── Hide default header & footer ── */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* ── Custom scrollbar ── */
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: #0E1117; }
    ::-webkit-scrollbar-thumb { background: #00D4AA40; border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: #00D4AA80; }

    /* ── Hero Banner ── */
    .hero-banner {
        background: linear-gradient(135deg, #0a0f1c 0%, #0d1926 30%, #0a2015 70%, #0a0f1c 100%);
        border: 1px solid #00D4AA25;
        border-radius: 16px;
        padding: 28px 36px;
        margin-bottom: 24px;
        position: relative;
        overflow: hidden;
    }
    .hero-banner::before {
        content: '';
        position: absolute;
        top: -50%;
        right: -10%;
        width: 300px;
        height: 300px;
        background: radial-gradient(circle, #00D4AA08 0%, transparent 70%);
        border-radius: 50%;
    }
    .hero-title {
        font-family: 'Inter', sans-serif;
        font-weight: 900;
        font-size: 32px;
        background: linear-gradient(135deg, #00D4AA, #00FFD5, #00D4AA);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
        letter-spacing: -0.5px;
    }
    .hero-subtitle {
        color: #8B949E;
        font-size: 14px;
        margin-top: 6px;
        font-weight: 400;
    }
    .hero-badge {
        display: inline-block;
        background: #00D4AA15;
        border: 1px solid #00D4AA40;
        color: #00D4AA;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 11px;
        font-weight: 600;
        letter-spacing: 1px;
        text-transform: uppercase;
        margin-top: 10px;
    }

    /* ── Metric Cards ── */
    .metric-card {
        background: linear-gradient(145deg, #161B22 0%, #1C2333 100%);
        border: 1px solid #30363D;
        border-radius: 12px;
        padding: 20px 24px;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
        overflow: hidden;
    }
    .metric-card:hover {
        border-color: #00D4AA50;
        box-shadow: 0 0 30px #00D4AA10;
        transform: translateY(-2px);
    }
    .metric-card::after {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 2px;
        background: linear-gradient(90deg, transparent, #00D4AA60, transparent);
    }
    .metric-label {
        color: #8B949E;
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        margin-bottom: 8px;
    }
    .metric-value {
        font-family: 'JetBrains Mono', monospace;
        font-size: 26px;
        font-weight: 700;
        color: #E6EDF3;
        margin: 0;
    }
    .metric-value.green { color: #00D4AA; }
    .metric-value.red { color: #FF6B6B; }
    .metric-value.gold { color: #FFD700; }
    .metric-delta {
        font-family: 'JetBrains Mono', monospace;
        font-size: 12px;
        font-weight: 600;
        margin-top: 6px;
    }
    .metric-delta.positive { color: #00D4AA; }
    .metric-delta.negative { color: #FF6B6B; }

    /* ── Section Headers ── */
    .section-header {
        font-family: 'Inter', sans-serif;
        font-weight: 700;
        font-size: 18px;
        color: #E6EDF3;
        margin: 28px 0 16px 0;
        padding-bottom: 10px;
        border-bottom: 2px solid #21262D;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .section-header .icon {
        font-size: 20px;
    }

    /* ── Trade Panel ── */
    .trade-panel {
        background: linear-gradient(145deg, #161B22 0%, #1C2333 100%);
        border: 1px solid #30363D;
        border-radius: 12px;
        padding: 24px;
    }
    
    /* ── Order Book Style ── */
    .order-row {
        font-family: 'JetBrains Mono', monospace;
        font-size: 13px;
        padding: 4px 0;
    }
    
    /* ── Status badges ── */
    .status-badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.5px;
    }
    .status-filled { background: #00D4AA20; color: #00D4AA; border: 1px solid #00D4AA40; }
    .status-new { background: #FFD70020; color: #FFD700; border: 1px solid #FFD70040; }
    .status-canceled { background: #FF6B6B20; color: #FF6B6B; border: 1px solid #FF6B6B40; }
    
    /* ── Buy/Sell buttons ── */
    .buy-btn {
        background: linear-gradient(135deg, #00D4AA, #00B894) !important;
        color: #0E1117 !important;
        font-weight: 700 !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 12px 0 !important;
        font-size: 15px !important;
        letter-spacing: 1px !important;
        width: 100% !important;
        transition: all 0.2s !important;
    }
    .sell-btn {
        background: linear-gradient(135deg, #FF6B6B, #EE5A5A) !important;
        color: #FFFFFF !important;
        font-weight: 700 !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 12px 0 !important;
        font-size: 15px !important;
        letter-spacing: 1px !important;
        width: 100% !important;
        transition: all 0.2s !important;
    }

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0D1117 0%, #0E1420 50%, #0D1117 100%);
        border-right: 1px solid #21262D;
    }
    .sidebar-brand {
        text-align: center;
        padding: 20px 0 10px 0;
    }
    .sidebar-brand h2 {
        font-family: 'Inter', sans-serif;
        font-weight: 900;
        font-size: 22px;
        background: linear-gradient(135deg, #00D4AA, #00FFD5);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
    }
    .sidebar-brand p {
        color: #484F58;
        font-size: 11px;
        letter-spacing: 2px;
        text-transform: uppercase;
        margin-top: 4px;
    }

    /* ── Ticker tape ── */
    .ticker-tape {
        display: flex;
        gap: 24px;
        overflow-x: auto;
        padding: 12px 0;
        margin-bottom: 8px;
    }
    .ticker-item {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 8px 16px;
        background: #161B2280;
        border: 1px solid #21262D;
        border-radius: 8px;
        white-space: nowrap;
        min-width: fit-content;
    }
    .ticker-symbol {
        font-family: 'JetBrains Mono', monospace;
        font-weight: 600;
        font-size: 13px;
        color: #E6EDF3;
    }
    .ticker-price {
        font-family: 'JetBrains Mono', monospace;
        font-weight: 700;
        font-size: 13px;
    }

    /* ── Animate pulse on live data ── */
    @keyframes pulse-green {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.6; }
    }
    .live-dot {
        display: inline-block;
        width: 8px;
        height: 8px;
        background: #00D4AA;
        border-radius: 50%;
        animation: pulse-green 2s infinite;
        margin-right: 6px;
        box-shadow: 0 0 6px #00D4AA80;
    }

    /* ── Table styling ── */
    .dataframe {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 12px !important;
    }

    /* ── Toast Notifications ── */
    div[data-testid="stToast"] {
        background: #161B22 !important;
        border: 1px solid #00D4AA40 !important;
        border-radius: 12px !important;
    }

    /* Hide streamlit branding */
    .viewerBadge_container__r5tak { display: none !important; }
    
    /* ── Custom tabs ── */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
        background: #0E1117;
        border-radius: 10px;
        padding: 4px;
        border: 1px solid #21262D;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 8px 20px;
        font-weight: 600;
        font-size: 13px;
    }
    .stTabs [aria-selected="true"] {
        background: #00D4AA15 !important;
        border-color: #00D4AA40 !important;
    }
</style>
""", unsafe_allow_html=True)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Sidebar
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

with st.sidebar:
    st.markdown("""
    <div class="sidebar-brand">
        <h2>₿ FUTURES TERMINAL</h2>
        <p>Binance Testnet</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # Symbol selector
    selected_symbol = st.selectbox(
        "🔍 SELECT PAIR",
        SUPPORTED_SYMBOLS,
        index=0,
        help="Choose a trading pair"
    )

    # Timeframe selector
    timeframe = st.selectbox(
        "⏱️ CHART TIMEFRAME",
        ["1m", "5m", "15m", "30m", "1h", "4h", "1d"],
        index=4,
        help="Candlestick chart timeframe"
    )

    st.markdown("---")

    # Connection status
    ping_result = api_get("/fapi/v1/ping")
    if isinstance(ping_result, dict) and not ping_result.get("error"):
        st.markdown('<div style="text-align:center;"><span class="live-dot"></span><span style="color:#00D4AA;font-weight:600;font-size:13px;">CONNECTED</span></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="text-align:center;"><span style="color:#FF6B6B;font-weight:600;font-size:13px;">⚠ DISCONNECTED</span></div>', unsafe_allow_html=True)

    st.markdown("---")

    # Auto-refresh toggle
    auto_refresh = st.toggle("⚡ Auto-Refresh (10s)", value=False)
    if auto_refresh:
        time.sleep(10)
        st.rerun()

    st.markdown("---")
    st.markdown(
        '<div style="text-align:center;color:#484F58;font-size:11px;padding:10px 0;">'
        '⚠️ TESTNET ONLY<br>No real funds at risk'
        '</div>',
        unsafe_allow_html=True
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Hero Banner
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

icon = SYMBOL_ICONS.get(selected_symbol, "📊")
now_str = datetime.now().strftime("%b %d, %Y • %I:%M %p")

st.markdown(f"""
<div class="hero-banner">
    <p class="hero-title">{icon} {selected_symbol} Trading Terminal</p>
    <p class="hero-subtitle">Binance Futures USDT-M Testnet • {now_str}</p>
    <span class="hero-badge"><span class="live-dot"></span> LIVE DATA</span>
</div>
""", unsafe_allow_html=True)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Ticker Tape (top prices)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

all_prices = get_all_prices()
if all_prices:
    tape_html = '<div class="ticker-tape">'
    top_symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT"]
    for sym in top_symbols:
        if sym in all_prices:
            p = all_prices[sym]
            s_icon = SYMBOL_ICONS.get(sym, "")
            tape_html += f'''
            <div class="ticker-item">
                <span class="ticker-symbol">{s_icon} {sym.replace("USDT","")}</span>
                <span class="ticker-price" style="color:#00D4AA;">${p:,.2f}</span>
            </div>'''
    tape_html += '</div>'
    st.markdown(tape_html, unsafe_allow_html=True)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Price Metrics Row
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

stats = get_24h_stats(selected_symbol)
current_price_data = get_price(selected_symbol)
current_price = float(current_price_data.get("price", 0)) if isinstance(current_price_data, dict) else 0

if isinstance(stats, dict) and not stats.get("error"):
    change_pct = float(stats.get("priceChangePercent", 0))
    high_24h = float(stats.get("highPrice", 0))
    low_24h = float(stats.get("lowPrice", 0))
    volume_24h = float(stats.get("quoteVolume", 0))
    
    change_class = "positive" if change_pct >= 0 else "negative"
    change_color = "green" if change_pct >= 0 else "red"
    change_arrow = "▲" if change_pct >= 0 else "▼"

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">💰 Current Price</div>
            <p class="metric-value {change_color}">${current_price:,.2f}</p>
            <div class="metric-delta {change_class}">{change_arrow} {change_pct:+.2f}%</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">📈 24h High</div>
            <p class="metric-value green">${high_24h:,.2f}</p>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">📉 24h Low</div>
            <p class="metric-value red">${low_24h:,.2f}</p>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        vol_display = f"${volume_24h / 1e6:,.1f}M" if volume_24h > 1e6 else f"${volume_24h:,.0f}"
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">📊 24h Volume</div>
            <p class="metric-value gold">{vol_display}</p>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MAIN CONTENT: Chart + Trade Panel
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

chart_col, trade_col = st.columns([3, 1])


# ── Candlestick Chart ──
with chart_col:
    st.markdown(f'<div class="section-header"><span class="icon">📊</span> {selected_symbol} Chart — {timeframe.upper()}</div>', unsafe_allow_html=True)

    klines = get_klines(selected_symbol, timeframe)

    if not klines.empty:
        fig = go.Figure()

        # Candlesticks
        colors_up = "#00D4AA"
        colors_down = "#FF6B6B"

        fig.add_trace(go.Candlestick(
            x=klines["open_time"],
            open=klines["open"],
            high=klines["high"],
            low=klines["low"],
            close=klines["close"],
            increasing_line_color=colors_up,
            decreasing_line_color=colors_down,
            increasing_fillcolor=colors_up,
            decreasing_fillcolor=colors_down,
            name="Price",
        ))

        # Volume bars at bottom
        vol_colors = [colors_up if c >= o else colors_down 
                      for c, o in zip(klines["close"], klines["open"])]
        max_vol = klines["volume"].max()
        vol_scaled = klines["volume"] / max_vol * (klines["high"].max() - klines["low"].min()) * 0.15
        vol_base = klines["low"].min() - (klines["high"].max() - klines["low"].min()) * 0.05

        fig.add_trace(go.Bar(
            x=klines["open_time"],
            y=vol_scaled,
            base=vol_base,
            marker_color=vol_colors,
            opacity=0.3,
            name="Volume",
            showlegend=False,
        ))

        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="#0E1117",
            plot_bgcolor="#0E1117",
            xaxis=dict(
                gridcolor="#21262D",
                showgrid=True,
                gridwidth=0.5,
                rangeslider=dict(visible=False),
            ),
            yaxis=dict(
                gridcolor="#21262D",
                showgrid=True,
                gridwidth=0.5,
                side="right",
            ),
            margin=dict(l=0, r=60, t=20, b=40),
            height=500,
            showlegend=False,
            xaxis_rangeslider_visible=False,
            font=dict(family="JetBrains Mono, monospace", size=11, color="#8B949E"),
            hoverlabel=dict(
                bgcolor="#1C2333",
                bordercolor="#00D4AA",
                font_size=12,
                font_family="JetBrains Mono",
            ),
        )

        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    else:
        st.warning("Could not load chart data.")


# ── Trade Panel ──
with trade_col:
    st.markdown('<div class="section-header"><span class="icon">⚡</span> Quick Trade</div>', unsafe_allow_html=True)

    st.markdown('<div class="trade-panel">', unsafe_allow_html=True)

    # Order type tabs
    order_type_tab = st.radio(
        "Order Type",
        ["MARKET", "LIMIT", "STOP_LIMIT"],
        horizontal=True,
        label_visibility="collapsed",
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # Quantity
    quantity = st.number_input(
        "📦 Quantity",
        min_value=0.001,
        value=0.002,
        step=0.001,
        format="%.3f",
        help="Amount to trade"
    )

    # Price fields (conditional)
    limit_price = None
    stop_trigger_price = None

    if order_type_tab in ["LIMIT", "STOP_LIMIT"]:
        limit_price = st.number_input(
            "💵 Limit Price",
            min_value=0.01,
            value=float(current_price) if current_price > 0 else 100.0,
            step=0.01,
            format="%.2f",
        )

    if order_type_tab == "STOP_LIMIT":
        stop_trigger_price = st.number_input(
            "🛑 Stop Price",
            min_value=0.01,
            value=float(current_price * 0.98) if current_price > 0 else 100.0,
            step=0.01,
            format="%.2f",
        )

    # Notional value estimate
    notional = quantity * current_price if current_price > 0 else 0
    st.markdown(
        f'<div style="text-align:center;color:#8B949E;font-size:12px;font-family:JetBrains Mono;'
        f'padding:8px 0;">≈ ${notional:,.2f} USDT</div>',
        unsafe_allow_html=True
    )

    if notional > 0 and notional < 100:
        st.warning("⚠️ Min notional: $100", icon="⚠️")

    st.markdown("<br>", unsafe_allow_html=True)

    # BUY / SELL buttons
    bcol1, bcol2 = st.columns(2)

    with bcol1:
        buy_clicked = st.button("🟢 BUY / LONG", key="buy_btn", use_container_width=True, type="primary")

    with bcol2:
        sell_clicked = st.button("🔴 SELL / SHORT", key="sell_btn", use_container_width=True)

    # Handle order placement
    if buy_clicked or sell_clicked:
        side = "BUY" if buy_clicked else "SELL"
        api_type = order_type_tab if order_type_tab != "STOP_LIMIT" else "STOP"

        result = place_order(
            symbol=selected_symbol,
            side=side,
            order_type=api_type,
            quantity=quantity,
            price=limit_price,
            stop_price=stop_trigger_price,
        )

        if isinstance(result, dict) and not result.get("error"):
            order_id = result.get("orderId", "N/A")
            st.success(f"✅ Order placed! ID: {order_id}")
            st.balloons()
            # Clear cache to refresh data
            get_open_orders.clear() if hasattr(get_open_orders, 'clear') else None
        else:
            err_msg = result.get("msg", "Unknown error") if isinstance(result, dict) else str(result)
            st.error(f"❌ {err_msg}")

    st.markdown('</div>', unsafe_allow_html=True)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Bottom Panels: Account, Positions, Orders
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

tab_portfolio, tab_positions, tab_orders, tab_trades = st.tabs([
    "💰 Portfolio", "📈 Positions", "📋 Open Orders", "🔄 Recent Trades"
])


# ── Portfolio Tab ──
with tab_portfolio:
    account = get_account()
    if isinstance(account, dict) and not account.get("error"):
        assets = account.get("assets", [])
        nonzero_assets = [a for a in assets if float(a.get("walletBalance", 0)) > 0]

        if nonzero_assets:
            total_balance = sum(float(a["walletBalance"]) for a in nonzero_assets)
            total_pnl = sum(float(a.get("unrealizedProfit", 0)) for a in nonzero_assets)
            available = sum(float(a.get("availableBalance", 0)) for a in nonzero_assets)

            pc1, pc2, pc3 = st.columns(3)
            with pc1:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">💎 Total Balance</div>
                    <p class="metric-value gold">${total_balance:,.2f}</p>
                </div>""", unsafe_allow_html=True)
            with pc2:
                pnl_color = "green" if total_pnl >= 0 else "red"
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">📊 Unrealized PnL</div>
                    <p class="metric-value {pnl_color}">${total_pnl:+,.2f}</p>
                </div>""", unsafe_allow_html=True)
            with pc3:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">🏦 Available</div>
                    <p class="metric-value">${available:,.2f}</p>
                </div>""", unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            # Asset table
            df_assets = pd.DataFrame([
                {
                    "Asset": a["asset"],
                    "Wallet Balance": f"${float(a['walletBalance']):,.4f}",
                    "Available": f"${float(a.get('availableBalance', 0)):,.4f}",
                    "Unrealized PnL": f"${float(a.get('unrealizedProfit', 0)):+,.4f}",
                    "Margin Balance": f"${float(a.get('marginBalance', 0)):,.4f}",
                }
                for a in nonzero_assets
            ])
            st.dataframe(df_assets, use_container_width=True, hide_index=True)
        else:
            st.info("No assets with balance found.")
    else:
        st.error("Failed to fetch account data.")


# ── Positions Tab ──
with tab_positions:
    if isinstance(account, dict) and not account.get("error"):
        positions = account.get("positions", [])
        open_positions = [p for p in positions if float(p.get("positionAmt", 0)) != 0]

        if open_positions:
            for pos in open_positions:
                sym = pos["symbol"]
                amt = float(pos["positionAmt"])
                entry = float(pos["entryPrice"])
                pnl = float(pos.get("unrealizedProfit", 0))
                leverage = pos.get("leverage", "1")
                direction = "LONG 📈" if amt > 0 else "SHORT 📉"
                pnl_color = "green" if pnl >= 0 else "red"

                p_icon = SYMBOL_ICONS.get(sym, "📊")
                st.markdown(f"""
                <div class="metric-card" style="margin-bottom:12px;">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <div>
                            <div class="metric-label">{p_icon} {sym} • {direction} • {leverage}x</div>
                            <p class="metric-value" style="font-size:20px;">{abs(amt)} units @ ${entry:,.2f}</p>
                        </div>
                        <div style="text-align:right;">
                            <div class="metric-label">Unrealized PnL</div>
                            <p class="metric-value {pnl_color}" style="font-size:20px;">${pnl:+,.2f}</p>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown(
                '<div style="text-align:center;padding:40px;color:#484F58;">'
                '<div style="font-size:48px;margin-bottom:12px;">📭</div>'
                '<div style="font-size:14px;">No open positions</div>'
                '<div style="font-size:12px;margin-top:4px;">Place a trade to get started!</div>'
                '</div>',
                unsafe_allow_html=True
            )


# ── Open Orders Tab ──
with tab_orders:
    orders = get_open_orders(selected_symbol)
    if isinstance(orders, list) and len(orders) > 0:
        for order in orders:
            oid = order.get("orderId", "N/A")
            o_sym = order.get("symbol", "N/A")
            o_side = order.get("side", "N/A")
            o_type = order.get("type", "N/A")
            o_price = order.get("price", "0")
            o_qty = order.get("origQty", "0")
            o_status = order.get("status", "UNKNOWN")
            o_time = datetime.fromtimestamp(order.get("time", 0) / 1000).strftime("%H:%M:%S")

            side_color = "#00D4AA" if o_side == "BUY" else "#FF6B6B"
            
            oc1, oc2, oc3, oc4, oc5 = st.columns([2, 1, 1, 1, 1])
            with oc1:
                st.markdown(f'<span style="color:{side_color};font-weight:700;font-family:JetBrains Mono;">{o_side}</span> {o_sym} <span style="color:#8B949E;">({o_type})</span>', unsafe_allow_html=True)
            with oc2:
                st.markdown(f'<span style="font-family:JetBrains Mono;color:#E6EDF3;">Qty: {o_qty}</span>', unsafe_allow_html=True)
            with oc3:
                st.markdown(f'<span style="font-family:JetBrains Mono;color:#FFD700;">${float(o_price):,.2f}</span>', unsafe_allow_html=True)
            with oc4:
                st.markdown(f'<span style="color:#8B949E;font-size:12px;">{o_time}</span>', unsafe_allow_html=True)
            with oc5:
                if st.button("❌ Cancel", key=f"cancel_{oid}"):
                    cancel_result = cancel_order(o_sym, oid)
                    if isinstance(cancel_result, dict) and not cancel_result.get("error"):
                        st.success(f"Order {oid} cancelled!")
                        st.rerun()
                    else:
                        st.error("Failed to cancel order.")
            
            st.markdown('<hr style="border-color:#21262D;margin:4px 0;">', unsafe_allow_html=True)
    else:
        st.markdown(
            '<div style="text-align:center;padding:40px;color:#484F58;">'
            '<div style="font-size:48px;margin-bottom:12px;">📋</div>'
            '<div style="font-size:14px;">No open orders for {}</div>'
            '</div>'.format(selected_symbol),
            unsafe_allow_html=True
        )


# ── Recent Trades Tab ──
with tab_trades:
    trades = get_recent_trades(selected_symbol)
    if isinstance(trades, list) and len(trades) > 0:
        df_trades = pd.DataFrame([
            {
                "Time": datetime.fromtimestamp(t.get("time", 0) / 1000).strftime("%H:%M:%S"),
                "Price": f"${float(t.get('price', 0)):,.2f}",
                "Quantity": t.get("qty", "0"),
                "Quote Qty": f"${float(t.get('quoteQty', 0)):,.2f}",
                "Side": "🟢 BUY" if t.get("isBuyerMaker") else "🔴 SELL",
            }
            for t in trades[-20:]
        ])
        st.dataframe(df_trades, use_container_width=True, hide_index=True)
    else:
        st.info("No recent trades available.")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Footer
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

st.markdown("<br>", unsafe_allow_html=True)
st.markdown(
    '<div style="text-align:center;color:#30363D;font-size:11px;padding:20px 0;border-top:1px solid #21262D;">'
    '₿ Binance Futures Testnet Trading Terminal • Built with Streamlit & Plotly<br>'
    f'<span style="color:#484F58;">Session: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</span>'
    '</div>',
    unsafe_allow_html=True
)
