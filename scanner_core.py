import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np
import yfinance as yf

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Master F&O Universe with core indices and high-liquidity FII/DII backed equities
DEFAULT_UNIVERSE = [
    # Core Indices
    {"symbol": "^NSEI", "name": "NIFTY 50", "category": "Index", "sector": "Benchmark"},
    {"symbol": "^NSEBANK", "name": "BANK NIFTY", "category": "Index", "sector": "Banking"},
    {"symbol": "NIFTY_FIN_SERVICE.NS", "name": "FINNIFTY", "category": "Index", "sector": "Financial Services"},
    
    # Top Liquid F&O Stocks (BFSI, IT, Energy, Auto, Metals, FMCG, Pharma, Infra)
    {"symbol": "RELIANCE.NS", "name": "Reliance Industries", "category": "Equity", "sector": "Energy & Infra"},
    {"symbol": "HDFCBANK.NS", "name": "HDFC Bank", "category": "Equity", "sector": "Banking"},
    {"symbol": "ICICIBANK.NS", "name": "ICICI Bank", "category": "Equity", "sector": "Banking"},
    {"symbol": "INFY.NS", "name": "Infosys", "category": "Equity", "sector": "IT"},
    {"symbol": "TCS.NS", "name": "Tata Consultancy Services", "category": "Equity", "sector": "IT"},
    {"symbol": "SBIN.NS", "name": "State Bank of India", "category": "Equity", "sector": "Banking"},
    {"symbol": "BHARTIARTL.NS", "name": "Bharti Airtel", "category": "Equity", "sector": "Telecom"},
    {"symbol": "ITC.NS", "name": "ITC Ltd.", "category": "Equity", "sector": "FMCG"},
    {"symbol": "KOTAKBANK.NS", "name": "Kotak Mahindra Bank", "category": "Equity", "sector": "Banking"},
    {"symbol": "LT.NS", "name": "Larsen & Toubro", "category": "Equity", "sector": "Infrastructure"},
    {"symbol": "AXISBANK.NS", "name": "Axis Bank", "category": "Equity", "sector": "Banking"},
    {"symbol": "TATACONSUM.NS", "name": "Tata Consumer", "category": "Equity", "sector": "FMCG"},
    {"symbol": "MARUTI.NS", "name": "Maruti Suzuki", "category": "Equity", "sector": "Auto"},
    {"symbol": "SUNPHARMA.NS", "name": "Sun Pharma", "category": "Equity", "sector": "Pharma"},
    {"symbol": "BAJFINANCE.NS", "name": "Bajaj Finance", "category": "Equity", "sector": "NBFC"},
    {"symbol": "TATASTEEL.NS", "name": "Tata Steel", "category": "Equity", "sector": "Metals"},
    {"symbol": "HCLTECH.NS", "name": "HCL Technologies", "category": "Equity", "sector": "IT"},
    {"symbol": "M&M.NS", "name": "Mahindra & Mahindra", "category": "Equity", "sector": "Auto"},
    {"symbol": "ADANIENT.NS", "name": "Adani Enterprises", "category": "Equity", "sector": "Conglomerate"},
    {"symbol": "NTPC.NS", "name": "NTPC Ltd.", "category": "Equity", "sector": "Utilities"},
    {"symbol": "CIPLA.NS", "name": "Cipla", "category": "Equity", "sector": "Pharma"},
    {"symbol": "ONGC.NS", "name": "ONGC", "category": "Equity", "sector": "Energy"},
    {"symbol": "COALINDIA.NS", "name": "Coal India", "category": "Equity", "sector": "Mining"},
    {"symbol": "ULTRACEMCO.NS", "name": "UltraTech Cement", "category": "Equity", "sector": "Materials"},
    {"symbol": "POWERGRID.NS", "name": "Power Grid Corp", "category": "Equity", "sector": "Utilities"},
    {"symbol": "TITAN.NS", "name": "Titan Company", "category": "Equity", "sector": "Consumer Goods"},
    {"symbol": "HINDUNILVR.NS", "name": "Hindustan Unilever", "category": "Equity", "sector": "FMCG"},
    {"symbol": "ASIANPAINT.NS", "name": "Asian Paints", "category": "Equity", "sector": "Consumer Goods"},
    {"symbol": "BAJAJFINSV.NS", "name": "Bajaj Finserv", "category": "Equity", "sector": "Financial Services"},
    {"symbol": "JSWSTEEL.NS", "name": "JSW Steel", "category": "Equity", "sector": "Metals"},
    {"symbol": "HDFCLIFE.NS", "name": "HDFC Life", "category": "Equity", "sector": "Insurance"},
    {"symbol": "GRASIM.NS", "name": "Grasim Industries", "category": "Equity", "sector": "Materials"},
    {"symbol": "TECHM.NS", "name": "Tech Mahindra", "category": "Equity", "sector": "IT"},
    {"symbol": "HINDALCO.NS", "name": "Hindalco Industries", "category": "Equity", "sector": "Metals"},
    {"symbol": "WIPRO.NS", "name": "Wipro", "category": "Equity", "sector": "IT"},
    {"symbol": "EICHERMOT.NS", "name": "Eicher Motors", "category": "Equity", "sector": "Auto"},
    {"symbol": "SBILIFE.NS", "name": "SBI Life Insurance", "category": "Equity", "sector": "Insurance"},
    {"symbol": "DRREDDY.NS", "name": "Dr. Reddy's Lab", "category": "Equity", "sector": "Pharma"},
    {"symbol": "DIVISLAB.NS", "name": "Divi's Laboratories", "category": "Equity", "sector": "Pharma"},
    {"symbol": "BPCL.NS", "name": "BPCL", "category": "Equity", "sector": "Energy"},
    {"symbol": "APOLLOHOSP.NS", "name": "Apollo Hospitals", "category": "Equity", "sector": "Healthcare"},
    {"symbol": "BEL.NS", "name": "Bharat Electronics", "category": "Equity", "sector": "Defence"},
    {"symbol": "HAL.NS", "name": "Hindustan Aeronautics", "category": "Equity", "sector": "Defence"},
    {"symbol": "TRENT.NS", "name": "Trent Ltd.", "category": "Equity", "sector": "Retail"},
    {"symbol": "SHRIRAMFIN.NS", "name": "Shriram Finance", "category": "Equity", "sector": "NBFC"},
]


def calculate_atr(df: pd.DataFrame, period: int = 14) -> float:
    """Compute 14-period Daily True Range (ATR)."""
    if df is None or len(df) < period + 1:
        if df is not None and len(df) > 0:
            return float((df['High'] - df['Low']).mean())
        return 1.0

    high_low = df['High'] - df['Low']
    high_close_prev = (df['High'] - df['Close'].shift(1)).abs()
    low_close_prev = (df['Low'] - df['Close'].shift(1)).abs()

    tr = pd.concat([high_low, high_close_prev, low_close_prev], axis=1).max(axis=1)
    atr_series = tr.rolling(window=period).mean()
    atr_val = atr_series.iloc[-1]
    
    if pd.isna(atr_val) or atr_val <= 0:
        atr_val = float((df['High'] - df['Low']).iloc[-period:].mean())
        
    return float(atr_val) if (atr_val and atr_val > 0) else 1.0


def fetch_multi_timeframe_data(symbol: str) -> Optional[Dict[str, Any]]:
    """
    Fetch Daily, 4-Hour, Weekly, and 5m candles for a ticker symbol via yfinance with rate-limit resiliency.
    Computes structural static levels: PDH, PDL, PWH, PWL, 4H H, 4H L, 15m ORB, Daily Pivots, ATR(14).
    """
    try:
        ticker = yf.Ticker(symbol)
        
        # 1. Daily Data (Core Anchor for ATR, PDH/PDL, Pivots)
        try:
            df_daily = ticker.history(period="60d", interval="1d")
        except Exception:
            df_daily = pd.DataFrame()
            
        if df_daily.empty or len(df_daily) < 2:
            return None

        # 2. Weekly Data (for PWH/PWL with fallback)
        try:
            df_weekly = ticker.history(period="6mo", interval="1wk")
        except Exception:
            df_weekly = pd.DataFrame()
        
        # 3. Intraday 5m Data (for 15m ORB High/Low & 5m Charting with fallback)
        try:
            df_5m = ticker.history(period="5d", interval="5m")
        except Exception:
            df_5m = pd.DataFrame()

        if not df_5m.empty:
            latest_session_date = df_5m.index[-1].date()
            df_today_5m = df_5m[df_5m.index.date == latest_session_date]
            if not df_today_5m.empty:
                first_3_candles = df_today_5m.iloc[:min(3, len(df_today_5m))]
                orb_15m_high = float(first_3_candles['High'].max())
                orb_15m_low = float(first_3_candles['Low'].min())
            else:
                orb_15m_high = float(df_daily['High'].iloc[-1])
                orb_15m_low = float(df_daily['Low'].iloc[-1])
        else:
            orb_15m_high = float(df_daily['High'].iloc[-1])
            orb_15m_low = float(df_daily['Low'].iloc[-1])

        # 4. Intraday 60m Data (resampled to 4h with fallback)
        try:
            df_hourly = ticker.history(period="14d", interval="60m")
        except Exception:
            df_hourly = pd.DataFrame()

        if not df_hourly.empty:
            df_4h = df_hourly.resample('4h').agg({
                'Open': 'first',
                'High': 'max',
                'Low': 'min',
                'Close': 'last',
                'Volume': 'sum'
            }).dropna()
        else:
            df_4h = pd.DataFrame()

        # --- CALCULATE STRUCTURAL & EMA LEVELS ---
        close_series = df_daily['Close'].dropna()
        if close_series.empty:
            return None
        ltp = float(close_series.iloc[-1])
        atr_14 = calculate_atr(df_daily, period=14)

        # 8 EMA & 20 EMA Calculation
        ema_8_series = close_series.ewm(span=8, adjust=False).mean()
        ema_20_series = close_series.ewm(span=20, adjust=False).mean()
        
        ema_8 = float(ema_8_series.iloc[-1])
        ema_20 = float(ema_20_series.iloc[-1])
        
        if ema_8 > ema_20:
            ema_trend = "Bullish 🟢"
        elif ema_8 < ema_20:
            ema_trend = "Bearish 🔴"
        else:
            ema_trend = "Neutral ⚪"

        prev_day = df_daily.iloc[-2]
        pdh = float(prev_day['High'])
        pdl = float(prev_day['Low'])
        pdc = float(prev_day['Close'])

        # Daily Pivots (Classic Standard)
        pivot_p = (pdh + pdl + pdc) / 3.0
        r1 = (2 * pivot_p) - pdl
        s1 = (2 * pivot_p) - pdh
        r2 = pivot_p + (pdh - pdl)
        s2 = pivot_p - (pdh - pdl)

        # Previous Week High / Low
        if not df_weekly.empty and len(df_weekly) >= 2:
            prev_week = df_weekly.iloc[-2]
            pwh = float(prev_week['High'])
            pwl = float(prev_week['Low'])
        else:
            pwh = pdh
            pwl = pdl

        # 4-Hour High / Low
        if not df_4h.empty and len(df_4h) >= 2:
            prev_4h = df_4h.iloc[-2]
            h4_high = float(prev_4h['High'])
            h4_low = float(prev_4h['Low'])
        else:
            h4_high = float(df_daily['High'].iloc[-1])
            h4_low = float(df_daily['Low'].iloc[-1])

        levels = {
            "PDH": round(pdh, 2),
            "PDL": round(pdl, 2),
            "PWH": round(pwh, 2),
            "PWL": round(pwl, 2),
            "4H H": round(h4_high, 2),
            "4H L": round(h4_low, 2),
            "15m ORB H": round(orb_15m_high, 2),
            "15m ORB L": round(orb_15m_low, 2),
            "R1": round(r1, 2),
            "S1": round(s1, 2),
            "Pivot P": round(pivot_p, 2),
            "R2": round(r2, 2),
            "S2": round(s2, 2),
            "8 EMA": round(ema_8, 2),
            "20 EMA": round(ema_20, 2),
        }

        return {
            "symbol": symbol,
            "ltp": round(ltp, 2),
            "atr": round(atr_14, 2),
            "ema_8": round(ema_8, 2),
            "ema_20": round(ema_20, 2),
            "ema_trend": ema_trend,
            "orb_15m_high": round(orb_15m_high, 2),
            "orb_15m_low": round(orb_15m_low, 2),
            "levels": levels,
            "df_daily": df_daily,
            "df_hourly": df_hourly,
            "df_5m": df_5m,
            "timestamp": time.time()
        }

    except Exception as e:
        logger.error(f"Error fetching structural levels for {symbol}: {e}")
        return None


# Timeframe Hierarchy Level Weights
LEVEL_WEIGHTS = {
    # 3 Points: HTF Structural Levels (Major Liquidity Sweeps)
    "PDH": 3, "PDL": 3, "PWH": 3, "PWL": 3,
    # 2 Points: Intraday Structure, Pivots & 15m ORB
    "4H H": 2, "4H L": 2, "15m ORB H": 2, "15m ORB L": 2,
    "Pivot P": 2, "R1": 2, "S1": 2, "R2": 2, "S2": 2,
    # 1 Point: Dynamic EMAs
    "8 EMA": 1, "20 EMA": 1, "8 EMA (Bullish)": 1, "8 EMA (Bearish)": 1
}


class ProximityScanner:
    """Scanner core engine managing static levels cache & real-time ATR proximity calculation."""
    
    def __init__(self, universe: List[Dict[str, str]] = None, proximity_threshold: float = 0.35):
        self.universe = universe or DEFAULT_UNIVERSE
        self.proximity_threshold = proximity_threshold
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.last_cache_update = 0

    def load_static_levels(self, max_workers: int = 10) -> Dict[str, Dict[str, Any]]:
        """Fetch multi-timeframe static levels in parallel."""
        logger.info(f"Loading static levels for {len(self.universe)} symbols...")
        results = {}
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_item = {
                executor.submit(fetch_multi_timeframe_data, item["symbol"]): item 
                for item in self.universe
            }
            for future in as_completed(future_to_item):
                item = future_to_item[future]
                res = future.result()
                if res:
                    res["name"] = item["name"]
                    res["category"] = item["category"]
                    res["sector"] = item["sector"]
                    results[item["symbol"]] = res
        
        self.cache = results
        self.last_cache_update = time.time()
        logger.info(f"Loaded static levels for {len(results)} symbols successfully.")
        return results

    def scan_symbol(self, symbol_data: Dict[str, Any], live_ltp: Optional[float] = None) -> Dict[str, Any]:
        """
        Analyze price distance to structural levels normalized by ATR(14).
        Computes 3-2-1 Weighted Confluence Score (WCS) and Entry Zone.
        """
        ltp = live_ltp if live_ltp is not None else symbol_data["ltp"]
        atr = symbol_data["atr"] if symbol_data["atr"] > 0 else 1.0
        levels = symbol_data["levels"]

        level_distances = []
        clustered_levels = []

        for lvl_name, lvl_val in levels.items():
            dist_pts = abs(ltp - lvl_val)
            dist_atr = dist_pts / atr
            pct_diff = ((ltp - lvl_val) / ltp) * 100

            level_distances.append({
                "level_name": lvl_name,
                "level_price": lvl_val,
                "dist_pts": round(dist_pts, 2),
                "dist_atr": round(dist_atr, 3),
                "pct_diff": round(pct_diff, 2)
            })

            # Check if within proximity threshold
            if dist_atr <= self.proximity_threshold:
                if lvl_name == "8 EMA":
                    if symbol_data.get("ema_trend") == "Bullish 🟢":
                        clustered_levels.append("8 EMA (Bullish)")
                    elif symbol_data.get("ema_trend") == "Bearish 🔴":
                        clustered_levels.append("8 EMA (Bearish)")
                    else:
                        clustered_levels.append("8 EMA")
                else:
                    clustered_levels.append(lvl_name)

        # Sort levels by proximity distance in ATR
        level_distances.sort(key=lambda x: x["dist_atr"])
        nearest = level_distances[0]

        # Determine Confluence Direction Signal & 3-2-1 Weighted Score
        bullish_levels_set = {"PDL", "PWL", "4H L", "15m ORB L", "S1", "S2", "8 EMA (Bullish)"}
        bearish_levels_set = {"PDH", "PWH", "4H H", "15m ORB H", "R1", "R2", "8 EMA (Bearish)"}

        bullish_wcs = sum(LEVEL_WEIGHTS.get(lvl, 1) for lvl in clustered_levels if lvl in bullish_levels_set)
        bearish_wcs = sum(LEVEL_WEIGHTS.get(lvl, 1) for lvl in clustered_levels if lvl in bearish_levels_set)

        wcs_score = max(bullish_wcs, bearish_wcs)

        if bullish_wcs > bearish_wcs:
            signal_direction = "Bullish Support 🟢"
        elif bearish_wcs > bullish_wcs:
            signal_direction = "Bearish Resistance 🔴"
        else:
            if ltp >= nearest["level_price"]:
                signal_direction = "Bullish Support 🟢"
            else:
                signal_direction = "Bearish Resistance 🔴"

        # --- AUTOMATED TRADE EXECUTION & ENTRY ZONE ---
        buffer_atr = max(0.15 * atr, 1.0)

        # Identify clustered level prices
        cluster_prices = []
        for lvl_name, lvl_val in levels.items():
            if abs(ltp - lvl_val) / atr <= self.proximity_threshold:
                cluster_prices.append(lvl_val)
        if not cluster_prices:
            cluster_prices = [nearest["level_price"]]

        entry_price = float(np.mean(cluster_prices))
        entry_zone_min = round(entry_price - (0.15 * atr), 2)
        entry_zone_max = round(entry_price + (0.15 * atr), 2)
        entry_zone_str = f"₹{entry_zone_min:,.2f} – ₹{entry_zone_max:,.2f}"

        if "Bullish" in signal_direction:
            stop_loss = min(cluster_prices) - buffer_atr
            risk_pts = entry_price - stop_loss
            if risk_pts <= 0:
                risk_pts = max(0.25 * atr, 2.0)
                stop_loss = entry_price - risk_pts
                
            target_1 = entry_price + (1.5 * risk_pts)
            target_2 = entry_price + (3.0 * risk_pts)
            rr_str = "1 : 1.50 (T1) / 1 : 3.00 (T2)"
        else:
            stop_loss = max(cluster_prices) + buffer_atr
            risk_pts = stop_loss - entry_price
            if risk_pts <= 0:
                risk_pts = max(0.25 * atr, 2.0)
                stop_loss = entry_price + risk_pts
                
            target_1 = entry_price - (1.5 * risk_pts)
            target_2 = entry_price - (3.0 * risk_pts)
            rr_str = "1 : 1.50 (T1) / 1 : 3.00 (T2)"

        # Weighted Confluence Status Evaluation
        confluence_count = len(clustered_levels)
        confluence_cluster_str = " + ".join(clustered_levels) if clustered_levels else nearest["level_name"]

        if wcs_score >= 5:
            status = "SUPER HOT (A+)"
            badge_color = "red"
        elif wcs_score >= 3:
            status = "HOT CONFLUENCE"
            badge_color = "orange"
        elif wcs_score >= 1 or nearest["dist_atr"] <= (self.proximity_threshold * 2.0):
            status = "WATCH"
            badge_color = "yellow"
        else:
            status = "NEUTRAL"
            badge_color = "gray"

        return {
            "symbol": symbol_data["symbol"],
            "name": symbol_data["name"],
            "category": symbol_data["category"],
            "sector": symbol_data["sector"],
            "ltp": ltp,
            "atr": atr,
            "ema_8": symbol_data.get("ema_8", 0),
            "ema_20": symbol_data.get("ema_20", 0),
            "ema_trend": symbol_data.get("ema_trend", "Neutral ⚪"),
            "signal_direction": signal_direction,
            "wcs_score": wcs_score,
            "status": status,
            "badge_color": badge_color,
            "confluence_count": confluence_count,
            "confluence_cluster": confluence_cluster_str,
            "nearest_level_name": nearest["level_name"],
            "nearest_level_price": nearest["level_price"],
            "nearest_dist_atr": nearest["dist_atr"],
            "nearest_dist_pts": nearest["dist_pts"],
            "nearest_pct_diff": nearest["pct_diff"],
            "entry_price": round(entry_price, 2),
            "entry_zone_min": entry_zone_min,
            "entry_zone_max": entry_zone_max,
            "entry_zone_str": entry_zone_str,
            "stop_loss": round(stop_loss, 2),
            "target_1": round(target_1, 2),
            "target_2": round(target_2, 2),
            "risk_pts": round(risk_pts, 2),
            "risk_reward_ratio": rr_str,
            "all_level_distances": level_distances,
            "all_levels": levels
        }

    def run_full_scan(self, threshold: Optional[float] = None) -> List[Dict[str, Any]]:
        """Run proximity & confluence scan across the entire cached universe."""
        if threshold is not None:
            self.proximity_threshold = threshold
            
        if not self.cache:
            self.load_static_levels()

        scan_results = []
        for symbol, data in self.cache.items():
            scanned = self.scan_symbol(data)
            scan_results.append(scanned)

        # Sort by Weighted Confluence Score (descending) and nearest ATR distance (ascending)
        scan_results.sort(key=lambda x: (-x["wcs_score"], -x["confluence_count"], x["nearest_dist_atr"]))
        return scan_results

    def run_historical_backtest(self, symbol: str, lookback_days: int = 20) -> Dict[str, Any]:
        """
        Backtest how key level & confluence proximity trades performed on historical daily candles.
        Iterates over the past N trading sessions, computing static levels & testing target/SL hits.
        """
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period="120d", interval="1d")
            if df.empty or len(df) < lookback_days + 16:
                return {"error": f"Insufficient historical data for {symbol}"}

            trades = []
            wins_t1 = 0
            wins_t2 = 0
            losses = 0
            total_r_return = 0.0

            # Iterate over lookback window
            end_idx = len(df)
            start_idx = max(16, end_idx - lookback_days)

            for i in range(start_idx, end_idx):
                day_date = df.index[i].strftime("%Y-%m-%d")
                sub_df = df.iloc[:i]
                
                # Daily ATR(14) up to day i-1
                atr = calculate_atr(sub_df, period=14)
                if atr <= 0:
                    atr = 1.0

                # Day i-1 levels
                prev_day = sub_df.iloc[-1]
                pdh = float(prev_day['High'])
                pdl = float(prev_day['Low'])
                pdc = float(prev_day['Close'])

                # Pivot levels
                pivot_p = (pdh + pdl + pdc) / 3.0
                r1 = (2 * pivot_p) - pdl
                s1 = (2 * pivot_p) - pdh
                r2 = pivot_p + (pdh - pdl)
                s2 = pivot_p - (pdh - pdl)

                # 8 & 20 EMA
                close_series = sub_df['Close'].dropna()
                ema_8 = float(close_series.ewm(span=8, adjust=False).mean().iloc[-1])
                ema_20 = float(close_series.ewm(span=20, adjust=False).mean().iloc[-1])
                ema_trend = "Bullish" if ema_8 > ema_20 else "Bearish"

                # Day i Price action
                day_open = float(df['Open'].iloc[i])
                day_high = float(df['High'].iloc[i])
                day_low = float(df['Low'].iloc[i])
                day_close = float(df['Close'].iloc[i])

                # Test Bullish Support Proximity
                support_levels = {"PDL": pdl, "S1": s1, "S2": s2}
                if ema_trend == "Bullish":
                    support_levels["8 EMA"] = ema_8

                for s_name, s_val in support_levels.items():
                    dist_atr = abs(day_low - s_val) / atr
                    if dist_atr <= self.proximity_threshold:
                        entry = day_open if abs(day_open - s_val) / atr <= self.proximity_threshold else s_val
                        sl = s_val - (0.15 * atr)
                        risk = entry - sl
                        if risk <= 0:
                            risk = 0.30 * atr
                            sl = entry - risk
                            
                        t1 = entry + (1.5 * risk)
                        t2 = entry + (3.0 * risk)

                        # Evaluate Outcome
                        if day_high >= t2:
                            outcome = "WIN (Target 2 🎯)"
                            r_earned = +3.0
                            wins_t2 += 1
                        elif day_high >= t1:
                            outcome = "WIN (Target 1 🎯)"
                            r_earned = +1.5
                            wins_t1 += 1
                        elif day_low <= sl:
                            outcome = "LOSS (Stop Loss 🛑)"
                            r_earned = -1.0
                            losses += 1
                        else:
                            outcome = "NEUTRAL / OPEN ⚪"
                            r_earned = ((day_close - entry) / risk)

                        total_r_return += r_earned

                        trades.append({
                            "Date": day_date,
                            "Direction": "Bullish Support 🟢",
                            "Level Tested": s_name,
                            "Entry Price": round(entry, 2),
                            "Stop Loss": round(sl, 2),
                            "Target 1": round(t1, 2),
                            "Target 2": round(t2, 2),
                            "Day High": round(day_high, 2),
                            "Day Low": round(day_low, 2),
                            "Outcome": outcome,
                            "R Return": round(r_earned, 2)
                        })
                        break  # 1 signal per day max

                # Test Bearish Resistance Proximity if no bullish trade triggered
                resistance_levels = {"PDH": pdh, "R1": r1, "R2": r2}
                if ema_trend == "Bearish":
                    resistance_levels["8 EMA"] = ema_8

                if not any(t["Date"] == day_date for t in trades):
                    for r_name, r_val in resistance_levels.items():
                        dist_atr = abs(day_high - r_val) / atr
                        if dist_atr <= self.proximity_threshold:
                            entry = day_open if abs(day_open - r_val) / atr <= self.proximity_threshold else r_val
                            sl = r_val + (0.15 * atr)
                            risk = sl - entry
                            if risk <= 0:
                                risk = 0.30 * atr
                                sl = entry + risk
                                
                            t1 = entry - (1.5 * risk)
                            t2 = entry - (3.0 * risk)

                            if day_low <= t2:
                                outcome = "WIN (Target 2 🎯)"
                                r_earned = +3.0
                                wins_t2 += 1
                            elif day_low <= t1:
                                outcome = "WIN (Target 1 🎯)"
                                r_earned = +1.5
                                wins_t1 += 1
                            elif day_high >= sl:
                                outcome = "LOSS (Stop Loss 🛑)"
                                r_earned = -1.0
                                losses += 1
                            else:
                                outcome = "NEUTRAL / OPEN ⚪"
                                r_earned = ((entry - day_close) / risk)

                            total_r_return += r_earned

                            trades.append({
                                "Date": day_date,
                                "Direction": "Bearish Resistance 🔴",
                                "Level Tested": r_name,
                                "Entry Price": round(entry, 2),
                                "Stop Loss": round(sl, 2),
                                "Target 1": round(t1, 2),
                                "Target 2": round(t2, 2),
                                "Day High": round(day_high, 2),
                                "Day Low": round(day_low, 2),
                                "Outcome": outcome,
                                "R Return": round(r_earned, 2)
                            })
                            break

            total_trades = len(trades)
            total_wins = wins_t1 + wins_t2
            win_rate = (total_wins / total_trades * 100) if total_trades > 0 else 0.0

            return {
                "symbol": symbol,
                "lookback_days": lookback_days,
                "total_trades": total_trades,
                "total_wins": total_wins,
                "wins_t1": wins_t1,
                "wins_t2": wins_t2,
                "losses": losses,
                "win_rate": round(win_rate, 1),
                "total_r_return": round(total_r_return, 2),
                "trades": trades
            }

        except Exception as e:
            logger.error(f"Error running backtest for {symbol}: {e}")
            return {"error": str(e)}


if __name__ == "__main__":
    print("Testing scanner_core.py execution...")
    scanner = ProximityScanner(proximity_threshold=0.35)
    # Test single symbol first
    res_single = fetch_multi_timeframe_data("^NSEI")
    if res_single:
        print(f"Sample Ticker ^NSEI | LTP: {res_single['ltp']} | ATR(14): {res_single['atr']}")
        print("Levels:", res_single["levels"])
    
    # Test quick multi-symbol fetch
    scanner.universe = DEFAULT_UNIVERSE[:5]
    static_data = scanner.load_static_levels(max_workers=3)
    results = scanner.run_full_scan()
    print(f"Scanned {len(results)} symbols.")
    for r in results:
        sig = r['signal_direction'].encode('ascii', 'ignore').decode('ascii')
        print(f"{r['symbol']} ({r['name']}) | Signal: {sig} | Entry: Rs.{r['entry_price']} | SL: Rs.{r['stop_loss']} | T1: Rs.{r['target_1']} | T2: Rs.{r['target_2']} | R:R: {r['risk_reward_ratio']}")
