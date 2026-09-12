import time
import pandas as pd
import numpy as np
import streamlit as st

from scanner_core import ProximityScanner, DEFAULT_UNIVERSE

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Institutional Key-Level & Confluence Scanner",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- MODERN DARK GLASSMORPHIC STYLING ---
CUSTOM_CSS = """
<style>
    /* Dark Theme Core */
    .stApp {
        background-color: #0B0F19;
        color: #E5E7EB;
        font-family: 'Inter', system-ui, -apple-system, sans-serif;
    }
    
    /* Header Container */
    .header-box {
        background: linear-gradient(135deg, rgba(17, 24, 39, 0.8) 0%, rgba(31, 41, 55, 0.6) 100%);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 20px 24px;
        margin-bottom: 16px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
    }
    
    .header-title {
        font-size: 26px;
        font-weight: 800;
        background: linear-gradient(90deg, #3B82F6 0%, #60A5FA 50%, #93C5FD 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 6px;
    }
    
    .header-subtitle {
        font-size: 13px;
        color: #9CA3AF;
        line-height: 1.4;
    }
    
    /* Metric Cards */
    .metric-card {
        background: rgba(17, 24, 39, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 12px;
        padding: 12px;
        text-align: center;
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .metric-card:hover {
        border-color: rgba(59, 130, 246, 0.4);
        transform: translateY(-2px);
    }
    .metric-val {
        font-size: 22px;
        font-weight: 700;
        margin-top: 2px;
    }
    .metric-lbl {
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #9CA3AF;
    }
    
    /* Streamlit Overrides */
    div[data-testid="stSidebar"] {
        background-color: #0D121F;
        border-right: 1px solid rgba(255, 255, 255, 0.05);
    }
    .stDataFrame {
        border-radius: 12px;
        overflow: hidden;
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# --- INITIALIZE SCANNER STATE ---
if "scanner" not in st.session_state:
    st.session_state.scanner = ProximityScanner(proximity_threshold=0.35)

if "last_scan_time" not in st.session_state:
    st.session_state.last_scan_time = None

if "scan_results" not in st.session_state:
    st.session_state.scan_results = []


# --- SIDEBAR CONTROLS ---
with st.sidebar:
    st.image("https://img.icons8.com/isometric-line/100/3B82F6/line-chart.png", width=50)
    st.title("Scanner Controls")
    
    st.subheader("🎯 Proximity Threshold")
    atr_threshold = st.slider(
        "Max Distance (ATR 14)",
        min_value=0.10,
        max_value=1.00,
        value=0.35,
        step=0.05,
        help="Proximity threshold to trigger WATCH (1 level) or HOT CONFLUENCE (≥2 levels)."
    )
    
    st.markdown("---")
    st.subheader("⚡ Data Provider")
    data_source = st.radio(
        "Live Feed Source",
        options=["Free Live (yfinance)", "Angel One SmartAPI"],
        index=0
    )
    
    if data_source == "Angel One SmartAPI":
        st.caption("Configured in `.streamlit/secrets.toml`")
        api_key = st.text_input("SmartAPI Key", type="password", value=st.secrets.get("angel_one", {}).get("api_key", ""))
        client_code = st.text_input("Client Code", value=st.secrets.get("angel_one", {}).get("client_code", ""))
        if st.button("🔌 Connect SmartAPI"):
            st.info("Connecting to Angel One SmartAPI endpoint...")

    st.markdown("---")
    st.subheader("🔄 Refresh Options")
    auto_refresh = st.checkbox("Enable Auto-Refresh", value=False)
    refresh_sec = st.selectbox("Interval", options=[5, 10, 15, 30], index=1)
    
    if st.button("🚀 Run Live Scan Now", use_container_width=True, type="primary"):
        with st.spinner("Fetching multi-timeframe candles & scanning universe..."):
            st.session_state.scanner.load_static_levels()
            st.session_state.scan_results = st.session_state.scanner.run_full_scan(threshold=atr_threshold)
            st.session_state.last_scan_time = time.strftime("%H:%M:%S IST")
            st.success("Scan updated successfully!")


# --- MAIN HEADER ---
st.markdown("""
<div class="header-box">
    <div class="header-title">Institutional Key-Level & Confluence Proximity Scanner</div>
    <div class="header-subtitle">
        Real-time multi-timeframe scanner for NSE F&O equities & indices (Nifty 50, Bank Nifty, FinNifty).
        Normalized distance to <b>PDH/PDL, PWH/PWL, 4H H/L, 15m ORB, Daily Pivots, and 8/20 EMA</b>.
    </div>
</div>
""", unsafe_allow_html=True)


# Execute initial scan if empty or stale cache missing valid stop_loss values
if not st.session_state.scan_results or any(r.get("stop_loss", 0.0) == 0.0 for r in st.session_state.scan_results):
    with st.spinner("Initializing Master F&O Universe and Multi-Timeframe Levels..."):
        st.session_state.scanner.load_static_levels()
        st.session_state.scan_results = st.session_state.scanner.run_full_scan(threshold=atr_threshold)
        st.session_state.last_scan_time = time.strftime("%H:%M:%S IST")


results = st.session_state.scan_results

# --- KPI METRICS RIBBON ---
col1, col2, col3, col4, col5 = st.columns(5)

total_assets = len(results)
hot_count = sum(1 for r in results if r["status"] == "HOT CONFLUENCE")
watch_count = sum(1 for r in results if r["status"] == "WATCH")
near_count = sum(1 for r in results if r["status"] == "NEAR")
top_confluence = results[0]["symbol"].replace(".NS", "") if results else "N/A"

with col1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-lbl">Total Universe</div>
        <div class="metric-val" style="color: #60A5FA;">{total_assets}</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-lbl">🔥 Hot Confluences</div>
        <div class="metric-val" style="color: #EF4444;">{hot_count}</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-lbl">👁️ Watch State</div>
        <div class="metric-val" style="color: #F59E0B;">{watch_count}</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-lbl">⚡ Near Proximity</div>
        <div class="metric-val" style="color: #EAB308;">{near_count}</div>
    </div>
    """, unsafe_allow_html=True)

with col5:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-lbl">Top Clustered Asset</div>
        <div class="metric-val" style="color: #10B981; font-size: 18px; line-height: 1.5;">{top_confluence}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# Audio / Toast Alert Trigger
if hot_count > 0:
    st.toast(f"🚨 ALERT: {hot_count} assets triggered HOT CONFLUENCE within ≤ {atr_threshold} ATR!", icon="🔥")


# --- HELPER: MAP TICKER TO CLEAN TRADINGVIEW SYMBOL ---
def get_tv_symbol(sym: str) -> str:
    if sym == "^NSEI":
        return "NSE:NIFTY"
    elif sym == "^NSEBANK":
        return "NSE:BANKNIFTY"
    elif sym == "NIFTY_FIN_SERVICE.NS" or "FINNIFTY" in sym:
        return "NSE:FINNIFTY"

    clean = sym.replace(".NS", "").strip()
    if clean == "M&M":
        return "NSE:MM"
    elif clean == "M&MFIN":
        return "NSE:MMFIN"
    elif ":" not in clean:
        return f"NSE:{clean}"
    return clean


# --- MAIN FULL-WIDTH TABS LAYOUT ---
tab_matrix, tab_chart, tab_backtest, tab_pine = st.tabs([
    "📊 Confluence Scanner Matrix (Full Screen)",
    "📈 TradingView Live Chart (Full Screen & Account Sync)",
    "🧪 Historical Backtester (Past Performance)",
    "📜 Complete Pine Script v5 Indicator Code"
])

with tab_matrix:
    st.subheader("📊 Live Confluence Scan Matrix (3-2-1 Timeframe Weighted Scoring)")
    
    f_col1, f_col2, f_col3, f_col4, f_col5 = st.columns([2, 2, 2, 2, 3])
    with f_col1:
        status_filter = st.selectbox(
            "Status Filter",
            options=["All Statuses", "SUPER HOT (A+ ≥5 Pts)", "HOT CONFLUENCE (A ≥3 Pts)", "WATCH (B 1-2 Pts)"],
            index=0
        )
    with f_col2:
        signal_filter = st.selectbox(
            "Confluence Direction",
            options=["All Directions", "Bullish Support 🟢", "Bearish Resistance 🔴"],
            index=0
        )
    with f_col3:
        category_filter = st.selectbox(
            "Asset Class",
            options=["All", "Index", "Equity"],
            index=0
        )
    with f_col4:
        all_sectors = ["All"] + sorted(list(set(r["sector"] for r in results)))
        sector_filter = st.selectbox("Sector", options=all_sectors, index=0)
    with f_col5:
        search_query = st.text_input("🔍 Search Ticker / Name", value="")

    # Apply Filtering Logic
    filtered_results = []
    for r in results:
        if status_filter == "SUPER HOT (A+ ≥5 Pts)" and r["status"] != "SUPER HOT (A+)":
            continue
        elif status_filter == "HOT CONFLUENCE (A ≥3 Pts)" and r["status"] not in ["SUPER HOT (A+)", "HOT CONFLUENCE"]:
            continue
        elif status_filter == "WATCH (B 1-2 Pts)" and r["status"] != "WATCH":
            continue

        if signal_filter != "All Directions" and signal_filter not in r.get("signal_direction", ""):
            continue
            
        if category_filter != "All" and r["category"] != category_filter:
            continue

        if sector_filter != "All" and r["sector"] != sector_filter:
            continue
            
        if search_query:
            sq = search_query.lower()
            if sq not in r["symbol"].lower() and sq not in r["name"].lower():
                continue
                
        filtered_results.append(r)

    # Format Data for Display Table
    table_data = []
    for r in filtered_results:
        live_p = r.get("ltp", 0.0)
        entry_p = r.get("entry_price", live_p)
        sl_p = r.get("stop_loss", 0.0)
        t1_p = r.get("target_1", 0.0)
        t2_p = r.get("target_2", 0.0)
        risk_p = r.get("risk_pts", 0.0)
        wcs = r.get("wcs_score", 0)
        
        tv_sym = get_tv_symbol(r["symbol"])
        tv_url = f"https://in.tradingview.com/chart/?symbol={tv_sym}"
        
        table_data.append({
            "TradingView Link": tv_url,
            "Symbol": r["symbol"].replace(".NS", ""),
            "Name": r["name"],
            "Category": r["category"],
            "Sector": r["sector"],
            "Weighted Score (WCS)": f"{wcs} Pts",
            "EMA Trend": r.get("ema_trend", "Neutral ⚪"),
            "Confluence Signal": r.get("signal_direction", "Neutral ⚪"),
            "Live LTP (₹)": f"{live_p:,.2f}",
            "Entry Reaction Zone": r.get("entry_zone_str", f"₹{entry_p:,.2f}"),
            "Stop Loss SL (₹)": f"{sl_p:,.2f}",
            "Target 1 T1 (₹)": f"{t1_p:,.2f}",
            "Target 2 T2 (₹)": f"{t2_p:,.2f}",
            "Risk (Pts)": f"₹{risk_p:,.2f}",
            "R:R Ratio": r.get("risk_reward_ratio", "1:1.5"),
            "Nearest Level": r.get("nearest_level_name", "N/A"),
            "Distance (ATR)": f"{r.get('nearest_dist_atr', 0.0):.3f} ATR",
            "Confluence Cluster": r.get("confluence_cluster", ""),
            "Status": r.get("status", "NEUTRAL")
        })

    df_table = pd.DataFrame(table_data)

    if not df_table.empty:
        st.dataframe(
            df_table,
            use_container_width=True,
            hide_index=True,
            column_config={
                "TradingView Link": st.column_config.LinkColumn(
                    "Open Chart ↗️",
                    help="Click to open full TradingView chart in a new browser tab with your signed-in account & custom Pine Script indicators.",
                    validate="^https://",
                    display_text="📈 Open Chart ↗️"
                ),
                "Weighted Score (WCS)": st.column_config.TextColumn(
                    "WCS Score",
                    help="Timeframe Weighted Score: 3 Pts (Weekly/Daily), 2 Pts (4H/15m ORB/Pivots), 1 Pt (EMAs)",
                ),
                "Status": st.column_config.TextColumn(
                    "Status",
                    help="SUPER HOT (A+): ≥5 Pts. HOT CONFLUENCE (A): ≥3 Pts. WATCH: 1-2 Pts.",
                ),
                "Distance (ATR)": st.column_config.ProgressColumn(
                    "Distance (ATR)",
                    help="Normalized price distance to nearest level",
                    format="%.3f ATR",
                    min_value=0.0,
                    max_value=1.0
                )
            }
        )
        
        csv_bytes = df_table.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Scan Results (CSV)",
            data=csv_bytes,
            file_name=f"confluence_scan_{time.strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    else:
        st.warning("No assets match the selected filter criteria.")


with tab_chart:
    c_head1, c_head2 = st.columns([3, 2])
    with c_head1:
        st.subheader("📈 TradingView Live Interactive Chart")
    with c_head2:
        chart_selected_symbol = st.selectbox(
            "👉 Select Asset to Display Chart:",
            options=[r["symbol"] for r in results],
            index=0,
            key="chart_tab_symbol_select"
        )

    # Convert symbol for TradingView
    tv_symbol = get_tv_symbol(chart_selected_symbol)
    tv_direct_link = f"https://in.tradingview.com/chart/?symbol={tv_symbol}"
    
    col_link1, col_link2 = st.columns([3, 1])
    with col_link1:
        st.info("🔑 **TradingView Sign-In:** To load your saved Pine Scripts and indicators, click the button on the right to open directly in TradingView with your signed-in account!")
    with col_link2:
        st.link_button(
            f"🚀 Open {chart_selected_symbol.replace('.NS', '')} in New Tab ↗️",
            tv_direct_link,
            type="primary",
            use_container_width=True
        )

    # Embed TradingView Advanced Widget
    tv_container_id = f"tv_chart_{tv_symbol.replace(':', '_').replace('&', '_')}"
    tv_html = f"""
    <div class="tradingview-widget-container" style="height:720px;width:100%;">
      <div id="{tv_container_id}" style="height:720px;width:100%;"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
      <script type="text/javascript">
      new TradingView.widget({{
        "autosize": true,
        "symbol": "{tv_symbol}",
        "interval": "5",
        "timezone": "Asia/Kolkata",
        "theme": "dark",
        "style": "1",
        "locale": "en",
        "toolbar_bg": "#0D121F",
        "enable_publishing": true,
        "allow_symbol_change": true,
        "save_image": true,
        "show_popup_button": true,
        "popup_width": "1200",
        "popup_height": "800",
        "hide_side_toolbar": false,
        "withdateranges": true,
        "details": true,
        "hotlist": true,
        "calendar": true,
        "container_id": "{tv_container_id}"
      }});
      </script>
    </div>
    """
    st.components.v1.html(tv_html, height=730)

    # Display Selected Asset Trade Plan Card
    selected_result = next((r for r in results if r["symbol"] == chart_selected_symbol), None)

    if selected_result:
        is_bullish = "Bullish" in selected_result.get("signal_direction", "")
        card_color = "#10B981" if is_bullish else "#EF4444"
        trade_type = "BUY / LONG 🟢" if is_bullish else "SELL / SHORT 🔴"
        
        s_entry = selected_result.get("entry_price", selected_result.get("ltp", 0.0))
        s_ez = selected_result.get("entry_zone_str", f"₹{s_entry:,.2f}")
        s_sl = selected_result.get("stop_loss", 0.0)
        s_t1 = selected_result.get("target_1", 0.0)
        s_t2 = selected_result.get("target_2", 0.0)
        s_risk = selected_result.get("risk_pts", 0.0)
        s_wcs = selected_result.get("wcs_score", 0)

        st.markdown(f"""
        <div style="background: rgba(17, 24, 39, 0.8); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 16px; margin-top: 10px;">
            <div style="font-weight: 700; font-size: 16px; color: {card_color}; margin-bottom: 8px;">
                🎯 Actionable Trade Execution Plan for {chart_selected_symbol.replace('.NS', '')} ({trade_type}) | WCS Score: {s_wcs} Pts
            </div>
            <div style="display: flex; justify-content: space-between; font-size: 14px; color: #E5E7EB;">
                <div><b>Actionable Entry Zone:</b> <span style="color:#60A5FA;">{s_ez}</span></div>
                <div><b>Strict Stop Loss (SL):</b> <span style="color:#EF4444;">₹{s_sl:,.2f}</span></div>
                <div><b>Target 1 (1.5x):</b> <span style="color:#10B981;">₹{s_t1:,.2f}</span></div>
                <div><b>Target 2 (3.0x):</b> <span style="color:#F59E0B;">₹{s_t2:,.2f}</span></div>
                <div><b>Risk:</b> ₹{s_risk:,.2f}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)


with tab_backtest:
    st.subheader("🧪 Historical Backtester (Evaluate Performance over Past Weeks)")
    st.caption("Test how key-level confluence signals, target hits, and stop-loss levels performed on historical daily candles over the past 2 to 6 weeks.")

    bt_col1, bt_col2, bt_col3 = st.columns([3, 2, 2])

    with bt_col1:
        bt_symbol = st.selectbox(
            "Select Ticker to Backtest:",
            options=[r["symbol"] for r in results],
            key="bt_symbol_select"
        )

    with bt_col2:
        bt_lookback = st.selectbox(
            "Lookback Period:",
            options=[10, 20, 30, 45, 60],
            index=1,
            format_func=lambda x: f"Past {x} Trading Days (~{x//5} Weeks)"
        )

    with bt_col3:
        st.markdown("<br>", unsafe_allow_html=True)
        run_bt_btn = st.button("🚀 Run Backtest Now", type="primary", use_container_width=True)

    if run_bt_btn or "last_bt_result" in st.session_state:
        if run_bt_btn:
            with st.spinner(f"Running historical simulation for {bt_symbol} over past {bt_lookback} trading sessions..."):
                st.session_state.last_bt_result = st.session_state.scanner.run_historical_backtest(bt_symbol, lookback_days=bt_lookback)

        bt_res = st.session_state.get("last_bt_result", {})
        
        if bt_res and "error" not in bt_res:
            st.markdown(f"#### 📊 Backtest Summary for `{bt_res['symbol'].replace('.NS', '')}` (Past {bt_res['lookback_days']} Days)")
            
            b_col1, b_col2, b_col3, b_col4, b_col5 = st.columns(5)
            
            with b_col1:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-lbl">Win Rate</div>
                    <div class="metric-val" style="color: #10B981;">{bt_res['win_rate']}%</div>
                </div>
                """, unsafe_allow_html=True)

            with b_col2:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-lbl">Total Signals</div>
                    <div class="metric-val" style="color: #60A5FA;">{bt_res['total_trades']}</div>
                </div>
                """, unsafe_allow_html=True)

            with b_col3:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-lbl">Target Hits (T1/T2)</div>
                    <div class="metric-val" style="color: #10B981;">{bt_res['total_wins']}</div>
                </div>
                """, unsafe_allow_html=True)

            with b_col4:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-lbl">Stop Losses Hit</div>
                    <div class="metric-val" style="color: #EF4444;">{bt_res['losses']}</div>
                </div>
                """, unsafe_allow_html=True)

            with b_col5:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-lbl">Net Return (R-Units)</div>
                    <div class="metric-val" style="color: #F59E0B;">+{bt_res['total_r_return']} R</div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            
            if bt_res.get("trades"):
                df_bt = pd.DataFrame(bt_res["trades"])
                st.dataframe(df_bt, use_container_width=True, hide_index=True)
            else:
                st.info("No level proximity signals triggered in the chosen backtest window.")
        elif bt_res and "error" in bt_res:
            st.error(bt_res["error"])


with tab_pine:
    st.subheader("📜 Complete Pine Script v5 Indicator for TradingView")
    st.markdown(r"""
    This Pine Script v5 indicator implements **3-2-1 Timeframe Weighted Scoring (WCS)** & plots **Shaded Entry Reaction Zones** directly on your TradingView charts:
    - 🟢 **3 Points (HTF Structural Levels)**: Previous Day High/Low (`PDH`/`PDL`), Previous Week High/Low (`PWH`/`PWL`).
    - 🔵 **2 Points (Intraday Structure & Pivots)**: 4-Hour High/Low (`4H H`/`4H L`), 15m ORB High/Low (`15m ORB`), Pivots (`P`, `R1`, `S1`, `R2`, `S2`).
    - 📈 **1 Point (Dynamic EMAs)**: 8 EMA & 20 EMA.
    - 🎯 **Shaded Entry Reaction Zone Channel**: Highlights the exact entry boundary ($\text{Level} \pm 0.15 \times \text{ATR}$) to observe price action reactions.
    - 🔥 **Confluence Alerts**: Visual labels (`🔥 A+ BULLISH SUPPORT ZONE` / `🔥 A+ BEARISH RESISTANCE ZONE`) plotted when WCS Score $\ge 5$ Points.
    - 📊 **On-Chart Live Table**: Displays ATR, active bullish/bearish WCS score, status, Entry Zone, Stop Loss, and Targets (T1/T2).
    """)

    full_pinescript_code = """//@version=5
indicator("Institutional Multi-Timeframe Key-Level & 3-2-1 Confluence Scanner", overlay=true, max_lines_count=500, max_labels_count=500)

// --- USER INPUTS ---
atr_period      = input.int(14, "ATR Period (14)", minval=1, group="Parameters")
atr_proximity   = input.float(0.35, "Confluence Proximity Threshold (in ATR)", step=0.05, group="Parameters")
show_htf_levels = input.bool(true, "Show HTF Levels (PDH/PDL, PWH/PWL, 4H H/L)", group="Display Options")
show_orb        = input.bool(true, "Show 15-Min Opening Range (ORB)", group="Display Options")
show_pivots     = input.bool(true, "Show Daily Pivots (P, R1, S1, R2, S2)", group="Display Options")
show_emas       = input.bool(true, "Show 8 EMA & 20 EMA", group="Display Options")
show_entry_zone = input.bool(true, "Show Shaded Entry Reaction Zone Channel", group="Display Options")
show_dashboard  = input.bool(true, "Show Live On-Chart Confluence Dashboard", group="Display Options")

// --- ATR CALCULATION ---
atr14 = ta.atr(atr_period)

// --- MULTI-TIMEFRAME LEVEL FETCHING ---
// Daily Levels (3 Points for High/Low)
[pdh, pdl, pdc] = request.security(syminfo.tickerid, "D", [high[1], low[1], close[1]], lookahead=barmerge.lookahead_on)

// Daily Pivots Calculation (2 Points)
pivot_p = (pdh + pdl + pdc) / 3.0
r1 = (2 * pivot_p) - pdl
s1 = (2 * pivot_p) - pdh
r2 = pivot_p + (pdh - pdl)
s2 = pivot_p - (pdh - pdl)

// Weekly Levels (3 Points)
[pwh, pwl] = request.security(syminfo.tickerid, "W", [high[1], low[1]], lookahead=barmerge.lookahead_on)

// 4-Hour Levels (2 Points)
[h4_high, h4_low] = request.security(syminfo.tickerid, "240", [high[1], low[1]], lookahead=barmerge.lookahead_on)

// EMAs (1 Point)
ema8 = ta.ema(close, 8)
ema20 = ta.ema(close, 20)

// --- 15m OPENING RANGE (2 Points: 09:15 - 09:30 AM IST) ---
var float orb_high = na
var float orb_low = na

if ta.change(time("D")) != 0
    orb_high := high
    orb_low := low

if timeframe.isintraday and timeframe.multiplier <= 15 and session.isfirstbar
    orb_high := high
    orb_low := low

if na(orb_high)
    orb_high := pdh
if na(orb_low)
    orb_low := pdl

// --- PLOT LEVELS ON CHART ---
plot(show_htf_levels ? pdh : na, "PDH (3 pts)", color=color.new(#FF1744, 0), linewidth=2)
plot(show_htf_levels ? pdl : na, "PDL (3 pts)", color=color.new(#00E676, 0), linewidth=2)
plot(show_htf_levels ? pwh : na, "PWH (3 pts)", color=color.new(#D500F9, 0), linewidth=2)
plot(show_htf_levels ? pwl : na, "PWL (3 pts)", color=color.new(#FF9100, 0), linewidth=2)
plot(show_htf_levels ? h4_high : na, "4H High (2 pts)", color=color.new(#F50057, 20), linewidth=1, style=plot.style_dashed)
plot(show_htf_levels ? h4_low : na, "4H Low (2 pts)", color=color.new(#29B6F6, 20), linewidth=1, style=plot.style_dashed)

plot(show_pivots ? r2 : na, "R2 (2 pts)", color=color.new(#FF5252, 40), linewidth=1, style=plot.style_dotted)
plot(show_pivots ? r1 : na, "R1 (2 pts)", color=color.new(#FF1744, 20), linewidth=1)
plot(show_pivots ? pivot_p : na, "Pivot P (2 pts)", color=color.new(#E0E0E0, 20), linewidth=2)
plot(show_pivots ? s1 : na, "S1 (2 pts)", color=color.new(#69F0AE, 20), linewidth=1)
plot(show_pivots ? s2 : na, "S2 (2 pts)", color=color.new(#00E676, 40), linewidth=1, style=plot.style_dotted)

p_orb_h = plot(show_orb ? orb_high : na, "15m ORB High (2 pts)", color=color.new(#76FF03, 0), linewidth=2)
p_orb_l = plot(show_orb ? orb_low : na, "15m ORB Low (2 pts)", color=color.new(#FF3D00, 0), linewidth=2)
fill(p_orb_h, p_orb_l, color=color.new(#0288D1, 92), title="15m ORB Zone")

plot(show_emas ? ema8 : na, "8 EMA (1 pt)", color=color.new(#00E5FF, 0), linewidth=2)
plot(show_emas ? ema20 : na, "20 EMA (1 pt)", color=color.new(#FFD600, 0), linewidth=2)

// --- 3-2-1 WEIGHTED CONFLUENCE SCORE (WCS) ---
prox = atr14 * atr_proximity

int bull_wcs = 0
int bear_wcs = 0

// Support Level Weighted Checks
if math.abs(close - pdl) <= prox
    bull_wcs := bull_wcs + 3
if math.abs(close - pwl) <= prox
    bull_wcs := bull_wcs + 3
if math.abs(close - h4_low) <= prox
    bull_wcs := bull_wcs + 2
if math.abs(close - s1) <= prox
    bull_wcs := bull_wcs + 2
if math.abs(close - s2) <= prox
    bull_wcs := bull_wcs + 2
if math.abs(close - orb_low) <= prox
    bull_wcs := bull_wcs + 2
if ema8 > ema20 and math.abs(close - ema8) <= prox
    bull_wcs := bull_wcs + 1

// Resistance Level Weighted Checks
if math.abs(close - pdh) <= prox
    bear_wcs := bear_wcs + 3
if math.abs(close - pwh) <= prox
    bear_wcs := bear_wcs + 3
if math.abs(close - h4_high) <= prox
    bear_wcs := bear_wcs + 2
if math.abs(close - r1) <= prox
    bear_wcs := bear_wcs + 2
if math.abs(close - r2) <= prox
    bear_wcs := bear_wcs + 2
if math.abs(close - orb_high) <= prox
    bear_wcs := bear_wcs + 2
if ema8 < ema20 and math.abs(close - ema8) <= prox
    bear_wcs := bear_wcs + 1

bool is_super_bull = bull_wcs >= 5
bool is_hot_bull   = bull_wcs >= 3
bool is_super_bear = bear_wcs >= 5
bool is_hot_bear   = bear_wcs >= 3

// --- SHADED ENTRY REACTION ZONE CHANNEL & DYNAMIC LABELS ---
float entry_center = is_hot_bull ? close : (is_hot_bear ? close : na)
float entry_zone_top = not na(entry_center) ? entry_center + (0.15 * atr14) : na
float entry_zone_bot = not na(entry_center) ? entry_center - (0.15 * atr14) : na

p_ez_top = plot(show_entry_zone ? entry_zone_top : na, "Entry Zone Top", color=color.new(#00E676, 50), linewidth=1)
p_ez_bot = plot(show_entry_zone ? entry_zone_bot : na, "Entry Zone Bottom", color=color.new(#FF1744, 50), linewidth=1)
fill(p_ez_top, p_ez_bot, color=is_hot_bull ? color.new(#00E676, 85) : (is_hot_bear ? color.new(#FF1744, 85) : color.new(#29B6F6, 95)), title="Entry Reaction Zone Fill")

plotshape(is_super_bull and not is_super_bull[1], "SUPER HOT BULLISH SUPPORT", shape.labelup, location.belowbar, color.green, text="🔥 A+ BULLISH SUPPORT ZONE", textcolor=color.white, size=size.normal)
plotshape(is_super_bear and not is_super_bear[1], "SUPER HOT BEARISH RESISTANCE", shape.labeldown, location.abovebar, color.red, text="🔥 A+ BEARISH RESISTANCE ZONE", textcolor=color.white, size=size.normal)

// --- LIVE ON-CHART DASHBOARD ---
var table tbl = table.new(position.top_right, 2, 8, bgcolor=color.new(#0D121F, 10), border_color=color.new(#334155, 0), border_width=1)
if show_dashboard and barstate.islast
    table.cell(tbl, 0, 0, "3-2-1 CONFLUENCE SCANNER", bgcolor=#1E293B, text_color=color.white, text_size=size.small)
    table.cell(tbl, 1, 0, syminfo.ticker, bgcolor=#1E293B, text_color=color.cyan, text_size=size.small)
    
    table.cell(tbl, 0, 1, "ATR (14)", text_color=color.gray, text_size=size.small)
    table.cell(tbl, 1, 1, str.tostring(atr14, "#.##"), text_color=color.white, text_size=size.small)
    
    table.cell(tbl, 0, 2, "Bullish Support WCS", text_color=color.gray, text_size=size.small)
    table.cell(tbl, 1, 2, str.tostring(bull_wcs) + " Pts", text_color=bull_wcs >= 3 ? color.green : color.white, text_size=size.small)
    
    table.cell(tbl, 0, 3, "Bearish Resistance WCS", text_color=color.gray, text_size=size.small)
    table.cell(tbl, 1, 3, str.tostring(bear_wcs) + " Pts", text_color=bear_wcs >= 3 ? color.red : color.white, text_size=size.small)

    string status_txt = "NEUTRAL"
    color status_clr = color.gray
    if is_super_bull
        status_txt := "🔥 SUPER HOT SUPPORT (A+)"
        status_clr := color.green
    else if is_super_bear
        status_txt := "🔥 SUPER HOT RESISTANCE (A+)"
        status_clr := color.red
    else if is_hot_bull
        status_txt := "🟢 HOT SUPPORT (A)"
        status_clr := color.green
    else if is_hot_bear
        status_txt := "🔴 HOT RESISTANCE (A)"
        status_clr := color.red
    else if bull_wcs > 0 or bear_wcs > 0
        status_txt := "👁️ WATCH STATE (B)"
        status_clr := color.orange

    table.cell(tbl, 0, 4, "Confluence Status", text_color=color.gray, text_size=size.small)
    table.cell(tbl, 1, 4, status_txt, text_color=status_clr, text_size=size.small)

    table.cell(tbl, 0, 5, "Entry Reaction Zone", text_color=color.gray, text_size=size.small)
    table.cell(tbl, 1, 5, str.tostring(entry_zone_bot, "#.##") + " - " + str.tostring(entry_zone_top, "#.##"), text_color=color.cyan, text_size=size.small)

    float sl = is_hot_bull ? (close - (0.15 * atr14)) : (close + (0.15 * atr14))
    float risk = math.abs(close - sl)
    float t1 = is_hot_bull ? (close + (1.5 * risk)) : (close - (1.5 * risk))
    float t2 = is_hot_bull ? (close + (3.0 * risk)) : (close - (3.0 * risk))

    table.cell(tbl, 0, 6, "Est. Stop Loss", text_color=color.gray, text_size=size.small)
    table.cell(tbl, 1, 6, str.tostring(sl, "#.##"), text_color=color.red, text_size=size.small)

    table.cell(tbl, 0, 7, "Targets (T1 / T2)", text_color=color.gray, text_size=size.small)
    table.cell(tbl, 1, 7, str.tostring(t1, "#.##") + " / " + str.tostring(t2, "#.##"), text_color=color.green, text_size=size.small)
"""
    st.code(full_pinescript_code, language="pinescript")

    st.markdown("""
    #### 💡 How to Add this Script to your TradingView Account:
    1. Click the **Copy** icon in the top right of the code box above.
    2. Open [TradingView.com](https://in.tradingview.com) in your browser (signed in with your account).
    3. Open any chart, click **Pine Editor** at the bottom panel.
    4. Delete existing template text, paste this script, and click **Save**.
    5. Click **Add to chart**. All key levels, 15m ORBs, confluence signals, and live dashboard table will render automatically on any symbol!
    """)


# Auto-refresh loop handler
if auto_refresh:
    time.sleep(refresh_sec)
    st.rerun()


