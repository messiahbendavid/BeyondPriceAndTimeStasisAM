# -*- coding: utf-8 -*-
"""
Created on Wed Mar 11 19:26:54 2026

@author: brcum
"""

# -*- coding: utf-8 -*-
"""
STASIS AM — Alpha Markets Server  +  Market Stasis Index (MSI)
Deploy to: stasisAM.beyondpriceandtime.com

Copyright © 2026 Truth Communications LLC. All Rights Reserved.

Requirements:
    pip install dash dash-bootstrap-components pandas numpy
    pip install websocket-client requests gunicorn plotly
"""
import time
import threading
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque, defaultdict
from enum import Enum
import copy
import json
import os

import dash
from dash import dcc, html, Input, Output, State, callback_context, dash_table
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import websocket
import ssl
import requests

# ============================================================================
# CONFIG
# ============================================================================
POLYGON_API_KEY = os.environ.get(
    "POLYGON_API_KEY", "PnzhJOXEJO7tSpHr0ct2zjFKi6XO0yGi")


@dataclass
class Config:
    symbols: List[str] = field(default_factory=lambda: [
        "SPY", "AAPL", "NVDA", "TSLA", "AMD", "AMZN", "INTC", "PLTR",
        "BAC", "SOFI", "F", "GOOGL", "NIO", "MSFT", "META", "AAL",
        "SNAP", "CCL", "PFE", "T", "RIVN", "GOOG", "MARA", "UBER",
        "COIN", "VZ", "WFC", "NFLX", "KO", "LCID", "RIOT", "PYPL",
        "KVUE", "DIS", "VALE", "BABA", "CMCSA", "CSCO", "GM", "MU",
        "HOOD", "PARA", "MPW", "C", "CLSK", "JPM", "JNJ", "DAL",
        "WBA", "GRAB", "PBR", "GOLD", "AGNC", "AVGO", "JBLU", "XOM",
        "CVX", "SMCI", "KMI", "SQ", "SIRI", "BMY", "ET", "PCG",
        "TSM", "SCHW", "ABR", "PLUG", "DKNG", "HBAN", "LUV", "WBD",
        "NCLH", "RIG", "SHOP", "UAL", "DVN", "MS", "KEY", "ORCL",
        "OXY", "VFC", "ROKU", "TFC", "AFRM", "ARM", "HAL", "MO",
        "CLF", "WMT", "CHPT", "FCX", "PINS", "UPST", "GILD", "ABBV",
        "USB", "NU", "PDD", "QS", "SE", "ENVX", "RF", "JD", "SAVE",
        "SLB", "BRK.B", "CRM", "MRK", "NKLA", "PENN", "GS", "LI",
        "MGM", "UNH", "NEM", "BX", "XPEV", "ABNB", "BA", "COP",
        "AG", "WYNN", "ENPH", "AXP", "PM", "FSLR", "V", "MA",
        "LRCX", "COST", "UPS", "OPEN", "SBUX", "PANW", "ADBE",
        "MRVL", "ON", "IONQ", "AEM", "CRWD", "NOW", "VRT", "RBLX",
        "SPCE", "PATH", "TXN", "NKE", "DOW", "TELL", "QCOM", "LOW",
        "SNOW", "HD", "ANET", "SEDG", "BTU", "CAT", "DG", "MMM",
        "DASH", "MPC", "PSX", "FITB", "CZR", "BP", "LYFT", "LVS",
        "ASML", "SPOT", "EBAY", "MDT", "CVS", "RTX", "MTCH", "RKLB",
        "LLY", "HON", "SPWR", "APA", "EOSE", "BTI", "ZIM", "AFL",
        "EQT", "VLO", "BKR", "MRNA", "Z", "MRO", "DE", "LUMN",
        "AIG", "TEVA", "ZS", "CF", "TJX", "SWN", "CELH", "CMG",
        "TTWO", "AR", "U", "GE", "DHR", "STLA", "CL", "ALLY",
        "APD", "WPM", "BILI", "STX", "ETSY", "CPNG", "IMGN", "LAZR",
        "PG", "SNDL", "TTD", "NET", "AMC", "ADM", "DDOG", "MDB",
        "WDAY", "DELL", "STNG", "TWLO", "OKTA", "DOCU", "SU", "GSAT",
        "ZION", "FUBO", "CHWY", "WDC", "BLK", "TLRY", "CNC", "PEP",
        "BIDU", "ZM", "EL", "CARR", "FDX", "UEC", "ASTS", "CIG",
        "HPE", "CNP", "SYF", "ILMN", "TMO", "AZN", "AMGN", "PXD",
        "REGN", "ISRG", "RCL", "LEN", "TAL", "GPN", "D", "CTRA",
        "SO", "NEE", "DUK", "AEP", "SRE", "EXC", "VICI", "SPG",
        "O", "AMT", "CCI", "PLD", "WELL", "DLR", "EQIX", "PSA",
        "SBAC", "ARE", "AVB", "ARES", "KKR", "APO", "GDDY", "VEEV",
        "HPQ", "WHR", "CNX", "EDR", "NYCB", "COTY", "RUN", "GIS",
        "CPB", "HST", "IQ", "IP", "TRMB", "ACB", "CGC", "CRON",
        "TLRY", "DNA", "JOBY", "CIFR", "IREN", "HUT", "BITF", "BTBT",
        "CORZ", "WULF", "IBRX", "SOUN", "AI", "BBAI", "BIGC", "BLNK",
        "GOEV", "EVGO", "CHARX", "FSR", "MULN", "FFIE", "PSNY",
        "PTRA", "REE", "RIDE", "ARVL", "WKHS", "HYLN", "XL", "VTOL",
        "MP", "LAC", "ALB", "LTHM", "SLI", "PLL", "SGML", "ALTM",
        "SQM", "STNE", "PAGS", "DLO", "MELI", "GLOB", "VTEX",
        "CRSR", "LOGI", "HEAR", "GPRO", "SONO",
    ])
    etf_symbols: List[str] = field(default_factory=lambda: [
        "SPY", "QQQ", "IWM", "DIA", "XLF", "XLE", "XLU", "XLK",
        "XLP", "XLB", "XLV", "XLI", "XLY", "XLC", "XLRE", "KRE",
        "SMH", "XBI", "GDX",
    ])
    thresholds: List[float] = field(default_factory=lambda: [
        0.000625, 0.00125, 0.0025, 0.005, 0.0075, 0.01, 0.0125,
        0.015, 0.02, 0.025, 0.03, 0.04, 0.05, 0.10
    ])
    am_thresholds: List[float] = field(default_factory=lambda: [
        0.005, 0.0075, 0.01, 0.0125, 0.015, 0.02, 0.025, 0.03,
        0.04, 0.05
    ])
    # --- MSI config ---
    msi_sample_symbols: List[str] = field(default_factory=lambda: [])
    msi_default_threshold: float = 0.01
    msi_default_lookback: int = 90
    msi_lookback_options: List[int] = field(
        default_factory=lambda: [30, 60, 90, 180, 365])
    msi_threshold_options: List[float] = field(
        default_factory=lambda: [0.005, 0.01, 0.015, 0.02, 0.025, 0.03, 0.04, 0.05])

    update_interval_ms: int = 1000
    cache_refresh_interval: float = 0.5
    history_days: int = 5
    polygon_api_key: str = POLYGON_API_KEY
    polygon_ws_url: str = "wss://delayed.polygon.io/stocks"
    polygon_rest_url: str = "https://api.polygon.io"
    volumes: Dict[str, float] = field(default_factory=dict)
    week52_data: Dict[str, Dict] = field(default_factory=dict)
    fundamental_data: Dict[str, Dict] = field(default_factory=dict)
    fundamental_slopes: Dict[str, Dict] = field(default_factory=dict)
    correlation_data: Dict[str, Dict] = field(default_factory=dict)
    min_tradable_stasis: int = 3
    corr_window_quarters: int = 5


config = Config()
config.symbols = list(dict.fromkeys(config.symbols))
config.msi_sample_symbols = list(config.symbols)
# ============================================================================
# ENUMS & DATA CLASSES
# ============================================================================

class Direction(Enum):
    LONG = "LONG"
    SHORT = "SHORT"


class SignalStrength(Enum):
    WEAK = "WEAK"
    MODERATE = "MODERATE"
    STRONG = "STRONG"
    VERY_STRONG = "VERY_STRONG"


@dataclass
class BitEntry:
    bit: int
    price: float
    timestamp: datetime


@dataclass
class StasisInfo:
    start_time: datetime
    start_price: float
    peak_stasis: int = 1

    def get_duration(self) -> timedelta:
        return datetime.now() - self.start_time

    def get_duration_str(self) -> str:
        t = int(self.get_duration().total_seconds())
        if t < 60:
            return f"{t}s"
        if t < 3600:
            return f"{t // 60}m {t % 60}s"
        return f"{t // 3600}h {(t % 3600) // 60}m"

    def get_start_date_str(self) -> str:
        return self.start_time.strftime("%m/%d %H:%M")

    def get_price_change_pct(self, p: float) -> float:
        return (
            (p - self.start_price) / self.start_price * 100
            if self.start_price else 0)


# ============================================================================
# HELPERS
# ============================================================================
def calculate_52week_percentile(price, symbol):
    d = config.week52_data.get(symbol)
    if not d:
        return None
    h, l, r = d.get('high'), d.get('low'), d.get('range')
    if not all([h, l, r]) or r <= 0:
        return None
    return max(0, min(100, ((price - l) / r) * 100))


def fmt_slope(v):
    return "—" if v is None else f"{'+' if v >= 0 else ''}{v * 100:.1f}%"


def fmt_rr(rr):
    if rr is None:
        return "—"
    return "0:1" if rr <= 0 else (
        f"{rr:.2f}:1" if rr < 10 else f"{rr:.0f}:1")


def fmt_corr(v):
    if v is None:
        return "—"
    return f"{v:+.3f}"


def fmt_corr_delta(v):
    if v is None:
        return "—"
    arrow = "↘" if v < -0.05 else ("↗" if v > 0.05 else "→")
    return f"{arrow}{v:+.3f}"


# ============================================================================
# MARKET STASIS INDEX (MSI) ENGINE
# ============================================================================

class MarketStasisIndex:
    """
    Computes an aggregate Market Stasis Index from daily closes of a
    small sample of stocks.  For each stock on each trading day the
    bitstream algorithm is run over a *rolling window* of ``lookback``
    daily closes.  The MSI for that day is the mean stasis across all
    sample constituents.

    Extra dimensions derived from the same data:
        • MSI Breadth  — % of constituents with stasis ≥ 3
        • MSI Peak     — max single-stock stasis on that day
        • MSI Dispersion — std-dev of stasis values (0 = uniform)
    """

    def __init__(self):
        self.daily_closes: Dict[str, List[Tuple[str, float]]] = {}
        self._cache: Dict[Tuple[float, int], List[Dict]] = {}
        self._cache_lock = threading.Lock()
        self.data_fetched = False

    # ------------------------------------------------------------------ fetch
    def fetch_data(self, max_calendar_days: int = 400):
        """Download daily bars for every MSI sample symbol."""
        print("\n📈 MSI — Fetching daily closes for sample stocks …")
        end = datetime.now()
        start = end - timedelta(days=max_calendar_days)
        ok = fail = 0
        for sym in config.msi_sample_symbols:
            try:
                url = (
                    f"{config.polygon_rest_url}/v2/aggs/ticker/{sym}"
                    f"/range/1/day/"
                    f"{start.strftime('%Y-%m-%d')}/"
                    f"{end.strftime('%Y-%m-%d')}"
                    f"?adjusted=true&sort=asc&limit=5000"
                    f"&apiKey={config.polygon_api_key}")
                r = requests.get(url, timeout=15)
                if r.status_code == 200:
                    results = r.json().get('results', [])
                    if results:
                        self.daily_closes[sym] = [
                            (datetime.fromtimestamp(
                                b['t'] / 1000).strftime('%Y-%m-%d'),
                             b['c'])
                            for b in results
                        ]
                        ok += 1
                    else:
                        fail += 1
                else:
                    fail += 1
                time.sleep(0.12)
            except Exception as exc:
                print(f"  ⚠ MSI fetch {sym}: {exc}")
                fail += 1
        self.data_fetched = True
        print(f"✅ MSI daily data: {ok} ok, {fail} failed "
              f"({len(_sample_symbols)} requested)\n")

    # --------------------------------------------------------- core bitstream
    @staticmethod
    def _bitstream_final_stasis(
            closes: List[float], threshold: float) -> int:
        """Run the bitstream algorithm on *closes* and return the
        trailing-alternation stasis count at the end."""
        if len(closes) < 2:
            return 0
        ref = closes[0]
        bits: List[int] = []
        for price in closes[1:]:
            bw = threshold * ref
            if bw <= 0:
                continue
            if ref - bw < price < ref + bw:
                continue
            x = int((price - ref) / bw)
            if x > 0:
                bits.extend([1] * x)
                ref = price
            elif x < 0:
                bits.extend([0] * abs(x))
                ref = price
        # count trailing alternation
        if len(bits) < 2:
            return len(bits)
        cnt = 1
        for i in range(len(bits) - 1, 0, -1):
            if bits[i] != bits[i - 1]:
                cnt += 1
            else:
                break
        return cnt

    # ------------------------------------------------------ compute full MSI
    def compute(
            self,
            threshold: float = 0.01,
            lookback: int = 90) -> List[Dict]:
        """Return list of dicts, one per trading day, oldest first.

        Each dict::

            { 'date': '2024-06-12',
              'msi': 3.40,
              'breadth': 60.0,
              'peak': 7,
              'dispersion': 1.23,
              'components': {'SPY': 4, 'AAPL': 3, …},
              'num_stocks': 10 }
        """
        key = (threshold, lookback)
        with self._cache_lock:
            if key in self._cache:
                return self._cache[key]

        if not self.data_fetched or not self.daily_closes:
            return []

        # ---- per-symbol stasis series (keyed by date) --------------------
        sym_stasis: Dict[str, Dict[str, int]] = {}
        for sym, series in self.daily_closes.items():
            closes = [c for _, c in series]
            dates = [d for d, _ in series]
            stasis_by_date: Dict[str, int] = {}
            for i in range(len(closes)):
                win_start = max(0, i - lookback + 1)
                window = closes[win_start: i + 1]
                s = self._bitstream_final_stasis(window, threshold)
                stasis_by_date[dates[i]] = s
            sym_stasis[sym] = stasis_by_date

        # ---- aggregate by date -------------------------------------------
        all_dates: set = set()
        for sbd in sym_stasis.values():
            all_dates.update(sbd.keys())
        all_dates_sorted = sorted(all_dates)

        history: List[Dict] = []
        for dt in all_dates_sorted:
            vals: Dict[str, int] = {}
            for sym, sbd in sym_stasis.items():
                if dt in sbd:
                    vals[sym] = sbd[dt]
            if not vals:
                continue
            arr = list(vals.values())
            n = len(arr)
            msi_val = sum(arr) / n
            breadth = sum(1 for v in arr if v >= 3) / n * 100
            peak = max(arr)
            disp = float(np.std(arr)) if n > 1 else 0.0
            history.append({
                'date': dt,
                'msi': round(msi_val, 2),
                'breadth': round(breadth, 1),
                'peak': peak,
                'dispersion': round(disp, 2),
                'components': vals,
                'num_stocks': n,
            })

        with self._cache_lock:
            self._cache[key] = history
        return history

    # --------------------------------------------------- live MSI estimate
    def live_estimate(
            self,
            live_prices: Dict[str, float],
            threshold: float = 0.01,
            lookback: int = 90) -> Optional[Dict]:
        """Compute a *right-now* MSI by appending the latest live price
        to each symbol's daily series and computing stasis."""
        if not self.data_fetched or not self.daily_closes:
            return None
        today = datetime.now().strftime('%Y-%m-%d')
        vals: Dict[str, int] = {}
        for sym, series in self.daily_closes.items():
            lp = live_prices.get(sym)
            if lp is None:
                # fall back to last daily close
                if series:
                    lp = series[-1][1]
                else:
                    continue
            # build window: last lookback-1 daily closes + today's live
            closes = [c for _, c in series]
            dates = [d for d, _ in series]
            # if today already present, replace; else append
            if dates and dates[-1] == today:
                closes[-1] = lp
            else:
                closes.append(lp)
            window = closes[-(lookback):]
            s = self._bitstream_final_stasis(window, threshold)
            vals[sym] = s
        if not vals:
            return None
        arr = list(vals.values())
        n = len(arr)
        return {
            'date': today,
            'msi': round(sum(arr) / n, 2),
            'breadth': round(
                sum(1 for v in arr if v >= 3) / n * 100, 1),
            'peak': max(arr),
            'dispersion': round(
                float(np.std(arr)) if n > 1 else 0.0, 2),
            'components': vals,
            'num_stocks': n,
        }

    def invalidate_cache(self):
        with self._cache_lock:
            self._cache.clear()


msi_engine = MarketStasisIndex()


# ============================================================================
# PRICE:REVENUE CORRELATION ENGINE
# ============================================================================

def _corr_fetch_financials(symbol: str) -> Optional[Dict]:
    url = (f"{config.polygon_rest_url}/vX/reference/financials"
           f"?ticker={symbol}&timeframe=quarterly&limit=24"
           f"&sort=filing_date&order=desc&apiKey={config.polygon_api_key}")
    resp = requests.get(url, timeout=30)
    if resp.status_code != 200:
        return None
    results = resp.json().get('results', [])
    if not results:
        return None
    dates, revenue = [], []
    for r in results:
        try:
            fi = r.get('financials', {})
            inc = fi.get('income_statement', {})
            rev = inc.get('revenues', {}).get('value', 0) or 0
            fd = r.get('filing_date', '')
            if fd and rev != 0:
                dates.append(fd); revenue.append(rev)
        except Exception:
            continue
    return {'dates': dates[::-1], 'revenue': revenue[::-1]}


def _corr_fetch_daily_prices(symbol, start_date, end_date):
    url = (f"{config.polygon_rest_url}/v2/aggs/ticker/{symbol}/range/1/day/"
           f"{start_date}/{end_date}"
           f"?adjusted=true&sort=asc&limit=5000"
           f"&apiKey={config.polygon_api_key}")
    resp = requests.get(url, timeout=20)
    if resp.status_code != 200:
        return pd.DataFrame()
    results = resp.json().get('results', [])
    if not results:
        return pd.DataFrame()
    rows = [{'date': datetime.fromtimestamp(
        b['t'] / 1000).strftime('%Y-%m-%d'), 'close': b['c']}
        for b in results]
    return pd.DataFrame(rows)


def _corr_find_price_on_date(prices_df, target_date, max_lookback_days=10):
    if prices_df.empty or not target_date:
        return None
    try:
        target = pd.Timestamp(target_date)
    except Exception:
        return None
    df = prices_df.copy()
    df['dt'] = pd.to_datetime(df['date'])
    candidates = df[df['dt'] <= target]
    if candidates.empty:
        return None
    last_row = candidates.iloc[-1]
    if (target - last_row['dt']).days <= max_lookback_days:
        return float(last_row['close'])
    return None


def _corr_align_prices_to_quarters(financials, prices_df):
    rows = []
    for i in range(len(financials['dates'])):
        fd = financials['dates'][i]
        rows.append({
            'quarter': i, 'date': fd,
            'revenue': financials['revenue'][i],
            'price': _corr_find_price_on_date(prices_df, fd)})
    return pd.DataFrame(rows)


def _corr_pearson(prices, revenues):
    if len(prices) != len(revenues) or len(prices) < 3:
        return None
    if np.std(prices) < 1e-10 or np.std(revenues) < 1e-10:
        return None
    try:
        c = np.corrcoef(prices, revenues)[0, 1]
        return None if (np.isnan(c) or np.isinf(c)) else round(float(c), 4)
    except Exception:
        return None


def _corr_fetch_current_price(symbol):
    end = datetime.now(); start = end - timedelta(days=7)
    url = (f"{config.polygon_rest_url}/v2/aggs/ticker/{symbol}/range/1/day/"
           f"{start.strftime('%Y-%m-%d')}/{end.strftime('%Y-%m-%d')}"
           f"?adjusted=true&sort=desc&limit=5"
           f"&apiKey={config.polygon_api_key}")
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            results = resp.json().get('results', [])
            if results:
                return results[0]['c']
    except Exception:
        pass
    return None


def calculate_symbol_correlation(symbol):
    window = config.corr_window_quarters
    financials = _corr_fetch_financials(symbol)
    if not financials or len(financials['revenue']) < window:
        return None
    time.sleep(0.15)
    earliest_date = financials['dates'][0]
    try:
        start_date = (datetime.strptime(earliest_date, '%Y-%m-%d')
                      - timedelta(days=30)).strftime('%Y-%m-%d')
    except Exception:
        start_date = '2020-01-01'
    end_date = datetime.now().strftime('%Y-%m-%d')
    prices_df = _corr_fetch_daily_prices(symbol, start_date, end_date)
    if prices_df.empty:
        return None
    time.sleep(0.15)
    aligned = _corr_align_prices_to_quarters(financials, prices_df)
    current_price = _corr_fetch_current_price(symbol)
    if current_price is None and not prices_df.empty:
        current_price = prices_df.iloc[-1]['close']
    if current_price is None:
        return None
    time.sleep(0.15)
    result = {
        'symbol': symbol, 'corr_at_earnings': None,
        'corr_now': None, 'corr_delta': None,
        'decorrelation_score': None,
        'price_vs_rev_divergence': None,
        'earnings_date_price': None,
        'current_price': current_price,
        'price_change_since_earnings_pct': None,
        'latest_rev_change_pct': None, 'aligned_count': 0}
    valid = aligned.dropna(subset=['price']).copy().reset_index(drop=True)
    n = len(valid); result['aligned_count'] = n
    if n < window:
        return result
    tail = valid.tail(window).copy()
    tp = tail['price'].values.astype(float)
    tr = tail['revenue'].values.astype(float)
    ep = float(tp[-1]); result['earnings_date_price'] = round(ep, 2)
    corr_earn = _corr_pearson(tp, tr)
    result['corr_at_earnings'] = corr_earn
    if corr_earn is None:
        return result
    lp = tp.copy(); lp[-1] = current_price
    corr_now = _corr_pearson(lp, tr); result['corr_now'] = corr_now
    if corr_earn is not None and corr_now is not None:
        result['corr_delta'] = round(corr_now - corr_earn, 4)
    if ep > 0:
        result['price_change_since_earnings_pct'] = round(
            ((current_price - ep) / ep) * 100, 2)
    if n >= 2:
        rp = valid.iloc[-2]['revenue']; rc = valid.iloc[-1]['revenue']
        if rp and rp != 0:
            result['latest_rev_change_pct'] = round(
                ((rc - rp) / abs(rp)) * 100, 2)
    if corr_now is not None:
        ac = max(0, (1.0 - abs(corr_now)) * 0.5)
        dc = 0.0
        if result['corr_delta'] is not None:
            dc = max(0, min(0.5, (-result['corr_delta']) * 0.5))
        result['decorrelation_score'] = round(ac + dc, 4)
    pchg = result.get('price_change_since_earnings_pct')
    rchg = result.get('latest_rev_change_pct')
    if pchg is not None and rchg is not None:
        if pchg > rchg + 10:
            result['price_vs_rev_divergence'] = 'PRICE_AHEAD'
        elif rchg > pchg + 10:
            result['price_vs_rev_divergence'] = 'PRICE_BEHIND'
        else:
            result['price_vs_rev_divergence'] = 'ALIGNED'
    elif pchg is not None:
        if abs(pchg) > 15:
            result['price_vs_rev_divergence'] = (
                'PRICE_AHEAD' if pchg > 0 else 'PRICE_BEHIND')
        else:
            result['price_vs_rev_divergence'] = 'ALIGNED'
    return result


def calculate_all_correlations():
    print("\n📊 CALCULATING PRICE:REVENUE CORRELATIONS...")
    ok = fail = skip = 0
    for i, sym in enumerate(config.symbols):
        if sym in config.etf_symbols:
            skip += 1; continue
        try:
            result = calculate_symbol_correlation(sym)
            if result and result.get('corr_at_earnings') is not None:
                config.correlation_data[sym] = result; ok += 1
            elif result:
                config.correlation_data[sym] = result; fail += 1
            else:
                fail += 1
        except Exception:
            fail += 1
        if (i + 1) % 10 == 0:
            print(f"  --- Corr progress: {i+1}/{len(config.symbols)} "
                  f"(✓{ok} ✗{fail} ⏭{skip})")
    print(f"\n✅ Correlations: {ok} calculated, {fail} failed, "
          f"{skip} skipped\n")


# ============================================================================
# FUNDAMENTAL DATA
# ============================================================================
def fetch_fundamental_data_polygon(sym):
    try:
        url = (f"{config.polygon_rest_url}/vX/reference/financials"
               f"?ticker={sym}&timeframe=quarterly&limit=24"
               f"&sort=filing_date&order=desc"
               f"&apiKey={config.polygon_api_key}")
        resp = requests.get(url, timeout=30)
        if resp.status_code != 200:
            return None
        results = resp.json().get('results', [])
        if not results:
            return None
        fund = {k: [] for k in [
            'dates', 'revenue', 'net_income', 'operating_cash_flow',
            'capex', 'fcf', 'total_assets', 'total_liabilities',
            'shareholders_equity', 'current_assets',
            'current_liabilities', 'total_debt', 'eps']}
        for r in results:
            try:
                fi = r.get('financials', {})
                inc = fi.get('income_statement', {})
                cf = fi.get('cash_flow_statement', {})
                bs = fi.get('balance_sheet', {})
                rev = inc.get('revenues', {}).get('value', 0) or 0
                ni = inc.get('net_income_loss', {}).get('value', 0) or 0
                eps = (inc.get('basic_earnings_per_share', {})
                       .get('value', 0) or 0)
                ocf = (cf.get(
                    'net_cash_flow_from_operating_activities', {})
                    .get('value', 0) or 0)
                cx = (cf.get(
                    'net_cash_flow_from_investing_activities', {})
                    .get('value', 0) or 0)
                ta = bs.get('assets', {}).get('value', 0) or 0
                tl = bs.get('liabilities', {}).get('value', 0) or 0
                eq = bs.get('equity', {}).get('value', 0) or 0
                ca = bs.get('current_assets', {}).get('value', 0) or 0
                cl = bs.get('current_liabilities', {}).get('value', 0) or 0
                ltd = bs.get('long_term_debt', {}).get('value', 0) or 0
                std = bs.get('short_term_debt', {}).get('value', 0) or 0
                fund['dates'].append(r.get('filing_date', ''))
                fund['revenue'].append(rev)
                fund['net_income'].append(ni)
                fund['operating_cash_flow'].append(ocf)
                fund['capex'].append(abs(cx))
                fund['fcf'].append(ocf + cx)
                fund['total_assets'].append(ta)
                fund['total_liabilities'].append(tl)
                fund['shareholders_equity'].append(eq)
                fund['current_assets'].append(ca)
                fund['current_liabilities'].append(cl)
                fund['total_debt'].append(ltd + std)
                fund['eps'].append(eps)
            except Exception:
                continue
        for k in fund:
            fund[k] = fund[k][::-1]
        return fund
    except Exception:
        return None


def calculate_slopes(series, ss=4, sl=20):
    if not series or len(series) < 5:
        return None, None
    s = pd.Series(series).replace([np.inf, -np.inf], np.nan)
    s5 = s20 = None
    try:
        if len(s.dropna()) >= 5:
            e = s.ewm(span=ss, adjust=False).mean()
            if abs(e.iloc[-5]) > 0.0001:
                s5 = (e.iloc[-1] - e.iloc[-5]) / abs(e.iloc[-5])
    except Exception:
        pass
    try:
        if len(s.dropna()) >= 21:
            e = s.ewm(span=sl, adjust=False).mean()
            if abs(e.iloc[-21]) > 0.0001:
                s20 = (e.iloc[-1] - e.iloc[-21]) / abs(e.iloc[-21])
    except Exception:
        pass
    return s5, s20


def calculate_all_slopes(fund, ratios):
    sl = {}
    sl['Rev_Slope_5'], sl['Rev_Slope_20'] = calculate_slopes(
        fund.get('revenue', []))
    sl['FCF_Slope_5'], sl['FCF_Slope_20'] = calculate_slopes(
        fund.get('fcf', []))
    for n, k in [('P/E Ratio', 'pe_ratio'), ('Return on Equity', 'roe'),
                 ('Net Profit Margin', 'net_profit_margin'),
                 ('Debt to Equity Ratio', 'debt_to_equity')]:
        sl[f'{n}_Slope_5'], sl[f'{n}_Slope_20'] = calculate_slopes(
            ratios.get(k, []))
    fl = ratios.get('fcfy', [])
    sl['FCFY'] = fl[-1] if fl and fl[-1] is not None else None
    return sl


def fetch_all_fundamental_data():
    print("\n📊 FETCHING FUNDAMENTAL DATA...")
    ok = fail = 0
    for i, sym in enumerate(config.symbols):
        try:
            fund = fetch_fundamental_data_polygon(sym)
            if fund and len(fund.get('revenue', [])) >= 4:
                price = 100
                w = config.week52_data.get(sym, {})
                if w.get('high') and w.get('low'):
                    price = (w['high'] + w['low']) / 2
                eq = fund['shareholders_equity'][-1]
                mcap = eq * 2 if eq and eq > 0 else 1e9
                ratios = {k: [] for k in [
                    'pe_ratio', 'roe', 'net_profit_margin',
                    'debt_to_equity', 'fcfy']}
                for j in range(len(fund['revenue'])):
                    try:
                        eps = fund['eps'][j]
                        ratios['pe_ratio'].append(
                            price / eps if eps > 0 else None)
                        eq_j = fund['shareholders_equity'][j]
                        ratios['roe'].append(
                            fund['net_income'][j] / eq_j
                            if eq_j > 0 else None)
                        rev_j = fund['revenue'][j]
                        ratios['net_profit_margin'].append(
                            fund['net_income'][j] / rev_j
                            if rev_j else None)
                        ratios['debt_to_equity'].append(
                            fund['total_debt'][j] / eq_j
                            if eq_j > 0 else None)
                        if j >= 3:
                            ratios['fcfy'].append(
                                sum(fund['fcf'][max(0, j - 3):j + 1])
                                / mcap if mcap else None)
                        else:
                            ratios['fcfy'].append(None)
                    except Exception:
                        for k in ratios:
                            ratios[k].append(None)
                slopes = calculate_all_slopes(fund, ratios)
                config.fundamental_data[sym] = fund
                config.fundamental_slopes[sym] = slopes
                ok += 1
            else:
                fail += 1
        except Exception:
            fail += 1
        if (i + 1) % 25 == 0:
            print(f"  📈 {i+1}/{len(config.symbols)} (✓{ok} ✗{fail})")
        time.sleep(0.15)
    print(f"✅ Fundamentals: {ok} ok, {fail} failed\n")


# ============================================================================
# MERIT SCORING
# ============================================================================
def calculate_stasis_merit_score(snap):
    ms = 0
    st = snap.get('stasis', 0)
    for t, p in [(15, 10), (12, 9), (10, 8), (8, 7), (7, 6),
                 (6, 5), (5, 4), (4, 3), (3, 2), (2, 1)]:
        if st >= t:
            ms += p; break
    rr = snap.get('risk_reward')
    if rr:
        for t, p in [(3, 5), (2.5, 4), (2, 3), (1.5, 2), (1, 1)]:
            if rr >= t:
                ms += p; break
    ms += {'VERY_STRONG': 4, 'STRONG': 3, 'MODERATE': 2,
           'WEAK': 1}.get(snap.get('signal_strength', ''), 0)
    dur = snap.get('duration_seconds', 0)
    if dur >= 3600:
        ms += 3
    elif dur >= 1800:
        ms += 2
    elif dur >= 900:
        ms += 1
    return ms


def calculate_correlation_merit_score(symbol, direction):
    score = 0
    details = {
        'corr_at_earnings': None, 'corr_now': None,
        'corr_delta': None, 'decor_score': None,
        'divergence': None, 'corr_merit': 0}
    corr = config.correlation_data.get(symbol)
    if not corr or corr.get('corr_at_earnings') is None:
        return score, details
    details['corr_at_earnings'] = corr['corr_at_earnings']
    details['corr_now'] = corr.get('corr_now')
    details['corr_delta'] = corr.get('corr_delta')
    details['decor_score'] = corr.get('decorrelation_score')
    details['divergence'] = corr.get('price_vs_rev_divergence')
    decor = corr.get('decorrelation_score', 0) or 0
    for th, pts in [(0.7, 6), (0.55, 5), (0.4, 4),
                    (0.3, 3), (0.2, 2), (0.1, 1)]:
        if decor >= th:
            score += pts; break
    delta = corr.get('corr_delta')
    if delta is not None:
        for th, pts in [(-0.4, 4), (-0.25, 3), (-0.15, 2), (-0.05, 1)]:
            if delta <= th:
                score += pts; break
    divergence = corr.get('price_vs_rev_divergence')
    if divergence and direction:
        if divergence == 'PRICE_BEHIND' and direction == 'LONG':
            score += 3
        elif divergence == 'PRICE_AHEAD' and direction == 'SHORT':
            score += 3
        elif divergence == 'PRICE_AHEAD' and direction == 'LONG':
            score -= 1
        elif divergence == 'PRICE_BEHIND' and direction == 'SHORT':
            score -= 1
    score = max(0, score)
    details['corr_merit'] = score
    return score, details


def calculate_fundamental_merit_score(symbol, w52_pct):
    ms = 0; sd = {}
    slopes = config.fundamental_slopes.get(symbol, {})
    if not slopes:
        if w52_pct is not None:
            for t, p in [(5, 8), (15, 7), (25, 6), (35, 5),
                         (45, 4), (55, 3), (65, 2), (75, 1)]:
                if w52_pct <= t:
                    ms += p; break
        return ms, sd
    for lbl, key, tps in [
        ('Rev_5', 'Rev_Slope_5',
         [(0.30, 4), (0.20, 3), (0.10, 2), (0.05, 1)]),
        ('FCF_5', 'FCF_Slope_5',
         [(0.40, 4), (0.25, 3), (0.10, 2), (0.05, 1)]),
        ('ROE_5', 'Return on Equity_Slope_5',
         [(0.20, 2), (0.10, 1)]),
        ('NPM_5', 'Net Profit Margin_Slope_5',
         [(0.20, 2), (0.10, 1)])]:
        v = slopes.get(key); sd[lbl] = v
        if v is not None:
            for t, p in tps:
                if v >= t:
                    ms += p; break
    for lbl, key, tps in [
        ('PE_5', 'P/E Ratio_Slope_5',
         [(-0.25, 3), (-0.15, 2), (-0.05, 1)]),
        ('DE_5', 'Debt to Equity Ratio_Slope_5',
         [(-0.20, 2), (-0.10, 1)])]:
        v = slopes.get(key); sd[lbl] = v
        if v is not None:
            for t, p in tps:
                if v <= t:
                    ms += p; break
    if w52_pct is not None:
        for t, p in [(5, 8), (15, 7), (25, 6), (35, 5),
                     (45, 4), (55, 3), (65, 2), (75, 1)]:
            if w52_pct <= t:
                ms += p; break
    fcfy = slopes.get('FCFY'); sd['FCFY'] = fcfy
    if fcfy is not None:
        if fcfy >= 0.15:
            ms += 3
        elif fcfy >= 0.10:
            ms += 2
        elif fcfy >= 0.05:
            ms += 1
    return ms, sd


# ============================================================================
# DATA FETCHERS
# ============================================================================
def fetch_52_week_data():
    print("📊 Fetching 52-week data...")
    w52 = {}; end = datetime.now(); start = end - timedelta(days=365)
    ok = fail = 0
    for i, sym in enumerate(config.symbols):
        try:
            url = (
                f"{config.polygon_rest_url}/v2/aggs/ticker/{sym}"
                f"/range/1/day/"
                f"{start.strftime('%Y-%m-%d')}/{end.strftime('%Y-%m-%d')}"
                f"?adjusted=true&sort=asc&limit=365"
                f"&apiKey={config.polygon_api_key}")
            r = requests.get(url, timeout=15)
            if r.status_code == 200:
                res = r.json().get('results', [])
                if res:
                    hv = max(b['h'] for b in res)
                    lv = min(b['l'] for b in res)
                    w52[sym] = {'high': hv, 'low': lv,
                                'range': hv - lv,
                                'current': res[-1]['c']}
                    ok += 1
                else:
                    w52[sym] = {'high': None, 'low': None,
                                'range': None, 'current': None}
                    fail += 1
            else:
                w52[sym] = {'high': None, 'low': None,
                            'range': None, 'current': None}
                fail += 1
            if (i + 1) % 50 == 0:
                print(f"  52W: {i+1}/{len(config.symbols)} "
                      f"(✓{ok} ✗{fail})")
            time.sleep(0.12)
        except Exception:
            w52[sym] = {'high': None, 'low': None,
                        'range': None, 'current': None}
            fail += 1
    print(f"✅ 52-week: {ok} ok, {fail} failed\n")
    return w52


def fetch_volume_data():
    print("📊 Fetching volume data...")
    vols = {}; end = datetime.now(); start = end - timedelta(days=45)
    for i, sym in enumerate(config.symbols):
        try:
            url = (
                f"{config.polygon_rest_url}/v2/aggs/ticker/{sym}"
                f"/range/1/day/"
                f"{start.strftime('%Y-%m-%d')}/{end.strftime('%Y-%m-%d')}"
                f"?adjusted=true&sort=desc&limit=30"
                f"&apiKey={config.polygon_api_key}")
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                res = r.json().get('results', [])
                if res:
                    vols[sym] = (
                        sum(b['v'] for b in res) / len(res)) / 1e6
                else:
                    vols[sym] = 10.0
            else:
                vols[sym] = 10.0
            if (i + 1) % 50 == 0:
                print(f"  Vol: {i+1}/{len(config.symbols)}")
            time.sleep(0.12)
        except Exception:
            vols[sym] = 10.0
    print("✅ Volume loaded\n")
    return vols


def fetch_historical_bars(sym, days=5):
    bars = []; end = datetime.now(); start = end - timedelta(days=days)
    try:
        url = (
            f"{config.polygon_rest_url}/v2/aggs/ticker/{sym}/range/1/minute/"
            f"{start.strftime('%Y-%m-%d')}/{end.strftime('%Y-%m-%d')}"
            f"?adjusted=true&sort=asc&limit=50000"
            f"&apiKey={config.polygon_api_key}")
        r = requests.get(url, timeout=30)
        if r.status_code == 200:
            res = r.json().get('results', [])
            bars = [{'timestamp': datetime.fromtimestamp(b['t'] / 1000),
                     'close': b['c']} for b in res]
    except Exception:
        pass
    return bars


# ============================================================================
# BITSTREAM
# ============================================================================
class Bitstream:
    def __init__(self, symbol, threshold, initial_price, volume):
        self.symbol = symbol
        self.threshold = threshold
        self.initial_price = initial_price
        self.volume = volume
        self.is_etf = symbol in config.etf_symbols
        self.reference_price = initial_price
        self.current_live_price = initial_price
        self.last_price_update = datetime.now()
        self._update_bands()
        self.bits: deque = deque(maxlen=500)
        self.current_stasis = 0
        self.last_bit = None
        self.direction = None
        self.signal_strength = None
        self.stasis_info: Optional[StasisInfo] = None
        self.total_bits = 0
        self._lock = threading.Lock()

    def _update_bands(self):
        self.band_width = self.threshold * self.reference_price
        self.upper_band = self.reference_price + self.band_width
        self.lower_band = self.reference_price - self.band_width

    def process_price(self, price, timestamp):
        with self._lock:
            self.current_live_price = price
            self.last_price_update = timestamp
            if self.lower_band < price < self.upper_band:
                return
            if self.band_width <= 0:
                return
            x = int((price - self.reference_price) / self.band_width)
            if x > 0:
                for _ in range(x):
                    self.bits.append(BitEntry(1, price, timestamp))
                    self.total_bits += 1
                self.reference_price = price
                self._update_bands()
            elif x < 0:
                for _ in range(abs(x)):
                    self.bits.append(BitEntry(0, price, timestamp))
                    self.total_bits += 1
                self.reference_price = price
                self._update_bands()
            self._update_stasis(timestamp)

    def _update_stasis(self, ts):
        if len(self.bits) < 2:
            self.current_stasis = len(self.bits)
            self.last_bit = self.bits[-1].bit if self.bits else None
            self.direction = None
            self.signal_strength = None
            return
        bl = list(self.bits); sc = 1; si = len(bl) - 1
        for i in range(len(bl) - 1, 0, -1):
            if bl[i].bit != bl[i - 1].bit:
                sc += 1; si = i - 1
            else:
                break
        prev = self.current_stasis; self.current_stasis = sc
        self.last_bit = bl[-1].bit
        if prev < 2 and sc >= 2 and 0 <= si < len(bl):
            self.stasis_info = StasisInfo(
                bl[si].timestamp, bl[si].price, sc)
        elif (sc >= 2 and self.stasis_info
              and sc > self.stasis_info.peak_stasis):
            self.stasis_info.peak_stasis = sc
        elif prev >= 2 and sc < 2:
            self.stasis_info = None
        if sc >= 2:
            self.direction = (Direction.LONG if self.last_bit == 0
                              else Direction.SHORT)
            if sc >= 10:
                self.signal_strength = SignalStrength.VERY_STRONG
            elif sc >= 7:
                self.signal_strength = SignalStrength.STRONG
            elif sc >= 5:
                self.signal_strength = SignalStrength.MODERATE
            elif sc >= 3:
                self.signal_strength = SignalStrength.WEAK
            else:
                self.signal_strength = None
        else:
            self.direction = None; self.signal_strength = None

    def get_snapshot(self, live_price=None):
        with self._lock:
            p = (live_price if live_price is not None
                 else self.current_live_price)
            si = self.stasis_info
            tp = sl = rr = None
            distance_to_tp_pct = distance_to_sl_pct = None
            stasis_price_change_pct = None
            if si is not None:
                stasis_price_change_pct = si.get_price_change_pct(p)
            if self.direction and self.current_stasis >= 2:
                if self.direction == Direction.LONG:
                    tp, sl = self.upper_band, self.lower_band
                    reward, risk = tp - p, p - sl
                else:
                    tp, sl = self.lower_band, self.upper_band
                    reward, risk = p - tp, sl - p
                if risk > 0 and reward > 0:
                    rr = reward / risk
                elif risk > 0:
                    rr = 0.0
                if p > 0:
                    distance_to_tp_pct = (abs(tp - p) / p) * 100
                    distance_to_sl_pct = (abs(sl - p) / p) * 100
            return {
                'symbol': self.symbol, 'is_etf': self.is_etf,
                'threshold': self.threshold,
                'threshold_pct': self.threshold * 100,
                'stasis': self.current_stasis,
                'total_bits': self.total_bits,
                'current_price': p,
                'anchor_price': si.start_price if si else None,
                'direction': (self.direction.value
                              if self.direction else None),
                'signal_strength': (self.signal_strength.value
                                    if self.signal_strength else None),
                'is_tradable': (
                    self.current_stasis >= config.min_tradable_stasis
                    and self.direction is not None
                    and self.volume > 1.0),
                'stasis_start_str': (
                    si.get_start_date_str() if si else "—"),
                'stasis_duration_str': (
                    si.get_duration_str() if si else "—"),
                'duration_seconds': (
                    si.get_duration().total_seconds() if si else 0),
                'stasis_price_change_pct': stasis_price_change_pct,
                'take_profit': tp, 'stop_loss': sl,
                'risk_reward': rr,
                'distance_to_tp_pct': distance_to_tp_pct,
                'distance_to_sl_pct': distance_to_sl_pct,
                'week52_percentile': calculate_52week_percentile(
                    p, self.symbol),
                'volume': self.volume}


# ============================================================================
# PRICE FEED
# ============================================================================
class PolygonPriceFeed:
    def __init__(self):
        self.lock = threading.Lock()
        self.current_prices = {s: None for s in config.symbols}
        self.is_running = False; self.ws = None; self.message_count = 0

    def start(self):
        self.is_running = True
        threading.Thread(target=self._loop, daemon=True).start()
        print("✅ WebSocket starting...")

    def _loop(self):
        while self.is_running:
            try:
                self._connect()
            except Exception as e:
                print(f"WS err: {e}"); time.sleep(5)

    def _connect(self):
        def on_msg(ws, msg):
            try:
                data = json.loads(msg)
                for m in (data if isinstance(data, list) else [data]):
                    self._proc(m)
            except Exception:
                pass

        def on_open(ws):
            print("✅ WS connected")
            ws.send(json.dumps({
                "action": "auth",
                "params": config.polygon_api_key}))

        self.ws = websocket.WebSocketApp(
            config.polygon_ws_url,
            on_open=on_open, on_message=on_msg)
        self.ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})

    def _proc(self, msg):
        if (msg.get('ev') == 'status'
                and msg.get('status') == 'auth_success'):
            self._sub()
        elif msg.get('ev') in ('A', 'AM', 'T', 'Q'):
            sym = msg.get('sym', '') or msg.get('S', '')
            price = (msg.get('c') or msg.get('vw')
                     or msg.get('p') or msg.get('bp'))
            if price and sym in self.current_prices:
                with self.lock:
                    self.current_prices[sym] = float(price)
                    self.message_count += 1

    def _sub(self):
        for i in range(0, len(config.symbols), 50):
            batch = config.symbols[i:i + 50]
            self.ws.send(json.dumps({
                "action": "subscribe",
                "params": ",".join(f"A.{s}" for s in batch)}))
            time.sleep(0.1)
        print(f"📡 Subscribed {len(config.symbols)} symbols")

    def get_prices(self):
        with self.lock:
            return {k: v for k, v in self.current_prices.items() if v}

    def get_status(self):
        with self.lock:
            return {
                'connected': sum(
                    1 for v in self.current_prices.values() if v),
                'total': len(config.symbols),
                'messages': self.message_count}


price_feed = PolygonPriceFeed()


# ============================================================================
# BITSTREAM MANAGER
# ============================================================================
class BitstreamManager:
    def __init__(self):
        self.lock = threading.Lock()
        self.streams: Dict[Tuple[str, float], Bitstream] = {}
        self.is_running = False
        self.cached_am_data: List[Dict] = []
        self.cache_lock = threading.Lock()
        self.initialized = False
        self.backfill_complete = False
        self.backfill_progress = 0

    def backfill(self):
        print("\n" + "=" * 60)
        print("📜 BACKFILLING")
        print("=" * 60)
        hist = {}
        for i, sym in enumerate(config.symbols):
            bars = fetch_historical_bars(sym, config.history_days)
            if bars:
                hist[sym] = bars
            self.backfill_progress = int(
                (i + 1) / len(config.symbols) * 100)
            if (i + 1) % 25 == 0:
                print(f"  📊 {i+1}/{len(config.symbols)} "
                      f"({self.backfill_progress}%)")
            time.sleep(0.12)
        with self.lock:
            for sym, bars in hist.items():
                if not bars:
                    continue
                vol = config.volumes.get(sym, 10.0)
                for th in config.thresholds:
                    key = (sym, th)
                    self.streams[key] = Bitstream(
                        sym, th, bars[0]['close'], vol)
                    for bar in bars:
                        self.streams[key].process_price(
                            bar['close'], bar['timestamp'])
        self.initialized = True
        self.backfill_complete = True
        tradable = sum(
            1 for s in self.streams.values()
            if s.current_stasis >= config.min_tradable_stasis
            and s.direction is not None and s.volume > 1.0)
        print(f"✅ Streams: {len(self.streams)} | Tradable: {tradable}")
        print("=" * 60)

    def start(self):
        self.is_running = True
        threading.Thread(target=self._process, daemon=True).start()
        threading.Thread(target=self._cache, daemon=True).start()

    def _process(self):
        while self.is_running:
            time.sleep(0.1)
            if not self.backfill_complete:
                continue
            prices = price_feed.get_prices(); ts = datetime.now()
            with self.lock:
                for sym, p in prices.items():
                    for th in config.thresholds:
                        k = (sym, th)
                        if k in self.streams:
                            self.streams[k].process_price(p, ts)

    def _cache(self):
        while self.is_running:
            time.sleep(config.cache_refresh_interval)
            if not self.initialized:
                continue
            prices = price_feed.get_prices(); snaps = []
            with self.lock:
                for s in self.streams.values():
                    snaps.append(s.get_snapshot(prices.get(s.symbol)))
            am = self._build_am(snaps)
            with self.cache_lock:
                self.cached_am_data = am

    def _build_am(self, snaps):
        rows = []
        for s in snaps:
            if s['threshold'] not in config.am_thresholds:
                continue
            sms = calculate_stasis_merit_score(s)
            fms, sd = calculate_fundamental_merit_score(
                s['symbol'], s.get('week52_percentile'))
            cms, cd = calculate_correlation_merit_score(
                s['symbol'], s.get('direction'))
            tms = sms + fms + cms
            rows.append({**s, 'sms': sms, 'fms': fms,
                         'cms': cms, 'tms': tms,
                         'slope_details': sd,
                         'corr_details': cd})
        return rows

    def get_am_data(self):
        with self.cache_lock:
            return copy.deepcopy(self.cached_am_data)


manager = BitstreamManager()


# ============================================================================
# DASH APP
# ============================================================================

AM_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@400;600&display=swap');
body { background: #f5f0e8 !important; }
.title-font { font-family: 'Orbitron', sans-serif !important; }
.msi-card {
    background: #faf7f0;
    border: 2px solid #1a5c2a;
    border-radius: 8px;
    margin: 8px;
    box-shadow: 0 2px 12px rgba(26,92,42,0.12);
}
.msi-kpi {
    display: inline-block;
    text-align: center;
    padding: 6px 14px;
    margin: 4px;
    border-radius: 6px;
    background: #e8f5e9;
    border: 1px solid #c8e6c9;
    min-width: 90px;
}
.msi-kpi-val {
    font-family: 'Orbitron', sans-serif;
    font-size: 18px;
    font-weight: 700;
    color: #1a5c2a;
}
.msi-kpi-lbl {
    font-size: 8px;
    color: #666;
    text-transform: uppercase;
    letter-spacing: 1px;
}
"""

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.FLATLY],
    suppress_callback_exceptions=True)
app.title = "STASIS AM"
server = app.server

app.index_string = '''<!DOCTYPE html>
<html><head>
{%metas%}<title>{%title%}</title>{%favicon%}{%css%}
<style>''' + AM_CSS + '''</style>
</head><body>
{%app_entry%}<footer>{%config%}{%scripts%}{%renderer%}</footer>
</body></html>'''


# ========================== LAYOUT ==========================================
app.layout = html.Div([
    dcc.Store(id='fmode', data='tradable'),
    dcc.Store(id='msi-last-params', data=None),
    dcc.Interval(id='tick', interval=1000, n_intervals=0),
    dcc.Interval(id='msi-tick', interval=8000, n_intervals=0),

    # ---- Header -----------------------------------------------------------
    html.Div([
        html.Span("📈", style={'fontSize': '22px'}),
        html.Span(" STASIS AM", className="title-font ms-2",
                  style={'fontSize': '16px', 'fontWeight': '700',
                         'color': '#1a5c2a', 'letterSpacing': '2px'}),
        html.Span(" — ALPHA MARKETS", className="title-font",
                  style={'fontSize': '9px', 'color': '#888',
                         'letterSpacing': '1px'}),
    ], style={'padding': '8px'}),

    html.Div(id='status',
             style={'fontSize': '10px', 'padding': '4px 8px',
                    'background': '#e8f5e9', 'fontWeight': 'bold'}),

    # ===================================================================
    # MARKET STASIS INDEX PANEL
    # ===================================================================
    html.Div([
        # MSI header
        html.Div([
            html.Span("🌐", style={'fontSize': '18px'}),
            html.Span(" MARKET STASIS INDEX",
                      className="title-font ms-2",
                      style={'fontSize': '13px', 'fontWeight': '700',
                             'color': '#1a5c2a',
                             'letterSpacing': '2px'}),
            html.Span(" — Aggregate Directional Oscillation",
                      style={'fontSize': '9px', 'color': '#666',
                             'marginLeft': '8px'}),
        ], style={'padding': '8px 12px',
                  'borderBottom': '1px solid #c8e6c9'}),

        # MSI controls
        html.Div([
            html.Label("Lookback Window:",
                       style={'fontSize': '10px', 'fontWeight': '600',
                              'marginRight': '4px', 'color': '#333'}),
            dcc.Dropdown(
                id='msi-lookback',
                options=[{'label': f'{d} Days', 'value': d}
                         for d in config.msi_lookback_options],
                value=config.msi_default_lookback,
                clearable=False,
                style={'width': '110px', 'fontSize': '10px',
                       'display': 'inline-block'}),
            html.Label("Band Threshold:",
                       style={'fontSize': '10px', 'fontWeight': '600',
                              'marginLeft': '16px',
                              'marginRight': '4px', 'color': '#333'}),
            dcc.Dropdown(
                id='msi-threshold',
                options=[{'label': f'{t*100:.1f}%', 'value': t}
                         for t in config.msi_threshold_options],
                value=_default_threshold,
                clearable=False,
                style={'width': '90px', 'fontSize': '10px',
                       'display': 'inline-block'}),
            html.Span(
                f"  Sample: {', '.join(_sample_symbols)}",
                style={'fontSize': '9px', 'color': '#888',
                       'marginLeft': '16px'}),
        ], className="d-flex align-items-center",
           style={'padding': '6px 12px',
                  'background': '#f0ebe0',
                  'borderBottom': '1px solid #e0d8c8'}),

        # MSI KPI row
        html.Div(id='msi-kpis', style={'padding': '6px 12px'}),

        # MSI chart
        dcc.Graph(id='msi-chart',
                  config={'displayModeBar': False},
                  style={'height': '280px', 'padding': '0 8px'}),

        # MSI component table
        html.Div(id='msi-components',
                 style={'padding': '4px 12px 8px 12px'}),

    ], className="msi-card"),

    # ===================================================================
    # MAIN TABLE SECTION
    # ===================================================================

    # Filters
    html.Div([
        dbc.ButtonGroup([
            dbc.Button("ALL", id="f-all", size="sm", outline=True,
                       style={'fontSize': '9px'}),
            dbc.Button("TRADABLE", id="f-trad", size="sm",
                       outline=True, active=True,
                       style={'fontSize': '9px',
                              'color': '#1a5c2a'}),
            dbc.Button("DECORR", id="f-decorr", size="sm",
                       outline=True,
                       style={'fontSize': '9px',
                              'color': '#8b4513'},
                       className="ms-1"),
        ], size="sm", className="me-2"),
        dcc.Dropdown(
            id='f-dir',
            options=[{'label': x, 'value': x}
                     for x in ['ALL', 'LONG', 'SHORT']],
            value='ALL', clearable=False,
            style={'width': '80px', 'fontSize': '10px',
                   'display': 'inline-block'}),
        dcc.Dropdown(id='f-sort', options=[
            {'label': 'TMS ↓', 'value': 'tms'},
            {'label': 'FMS ↓', 'value': 'fms'},
            {'label': 'CMS ↓', 'value': 'cms'},
            {'label': 'DECORR ↓', 'value': 'decorr'},
            {'label': 'Δ CORR ↑', 'value': 'corr_delta'},
            {'label': 'STASIS ↓', 'value': 'stasis'},
            {'label': '52W ↑', 'value': '52w'},
        ], value='tms', clearable=False,
            style={'width': '100px', 'fontSize': '10px',
                   'display': 'inline-block', 'marginLeft': '4px'}),
    ], className="d-flex align-items-center p-1",
       style={'background': '#f5f0e8'}),

    # Main AM Table
    dash_table.DataTable(
        id='tbl',
        columns=[{'name': c, 'id': c} for c in [
            '✓', 'SYM', 'BAND', 'STS', 'DIR', 'SMS', 'FMS', 'CMS',
            'TMS', 'C@E', 'C@N', 'ΔCOR', 'DCOR', 'DIV', 'REV5',
            'FCF5', 'FCFY', '52W', 'PRICE', 'TP', 'SL', 'R:R',
            'DUR']],
        sort_action='native',
        style_table={'overflowY': 'auto', 'height': '65vh'},
        style_cell={
            'backgroundColor': '#faf7f0', 'color': '#1a1a1a',
            'padding': '3px 4px', 'fontSize': '10px',
            'fontFamily': 'Consolas, monospace',
            'whiteSpace': 'nowrap', 'textAlign': 'right',
            'border': '1px solid #ddd'},
        style_cell_conditional=[
            {'if': {'column_id': 'SYM'}, 'textAlign': 'left',
             'fontWeight': '700', 'color': '#1a5c2a'},
            {'if': {'column_id': 'DIR'}, 'textAlign': 'center'},
            {'if': {'column_id': 'DIV'}, 'textAlign': 'center',
             'fontSize': '8px'}],
        style_header={
            'backgroundColor': '#1a5c2a', 'color': '#fff',
            'fontWeight': '700', 'fontSize': '9px',
            'textAlign': 'center'},
        style_data_conditional=[
            {'if': {'filter_query': '{DIR} = "LONG"',
                    'column_id': 'DIR'},
             'color': '#1a8c3a', 'fontWeight': 'bold'},
            {'if': {'filter_query': '{DIR} = "SHORT"',
                    'column_id': 'DIR'},
             'color': '#cc2200', 'fontWeight': 'bold'},
            {'if': {'filter_query': '{STS} >= 10'},
             'backgroundColor': '#e8f5e9'},
            {'if': {'filter_query': '{STS} >= 7 && {STS} < 10'},
             'backgroundColor': '#f1f8e9'},
            {'if': {'column_id': 'PRICE'},
             'color': '#0055aa', 'fontWeight': '600'},
            {'if': {'column_id': 'TP'}, 'color': '#1a8c3a'},
            {'if': {'column_id': 'SL'}, 'color': '#cc2200'},
            {'if': {'filter_query': '{TMS} >= 35',
                    'column_id': 'TMS'},
             'backgroundColor': '#1a8c3a', 'color': '#fff'},
            {'if': {'filter_query': '{TMS} >= 25 && {TMS} < 35',
                    'column_id': 'TMS'},
             'backgroundColor': '#4caf50', 'color': '#fff'},
            {'if': {'filter_query': '{TMS} >= 15 && {TMS} < 25',
                    'column_id': 'TMS'},
             'backgroundColor': '#81c784', 'color': '#fff'},
            {'if': {'filter_query': '{CMS} >= 8',
                    'column_id': 'CMS'},
             'backgroundColor': '#e65100', 'color': '#fff'},
            {'if': {'filter_query': '{CMS} >= 5 && {CMS} < 8',
                    'column_id': 'CMS'},
             'backgroundColor': '#f57c00', 'color': '#fff'},
            {'if': {'filter_query': '{CMS} >= 3 && {CMS} < 5',
                    'column_id': 'CMS'},
             'backgroundColor': '#ffb74d', 'color': '#000'},
            {'if': {'filter_query': '{DIV} = "P>R"',
                    'column_id': 'DIV'},
             'backgroundColor': '#fff3e0', 'color': '#e65100'},
            {'if': {'filter_query': '{DIV} = "P<R"',
                    'column_id': 'DIV'},
             'backgroundColor': '#e8f5e9', 'color': '#1b5e20'},
            {'if': {'row_index': 'odd'},
             'backgroundColor': '#f0ebe0'}],
        tooltip_header={
            'C@E': 'Correlation at last earnings date',
            'C@N': 'Correlation now (with live price)',
            'ΔCOR': 'Delta: C@N minus C@E (neg = decorrelating)',
            'DCOR': 'Decorrelation score (0-1)',
            'CMS': 'Correlation Merit Score',
            'DIV': 'Price vs Revenue divergence'}),

    html.Div(
        "© 2026 Truth Communications LLC • STASIS AM",
        className="text-center",
        style={'fontSize': '8px', 'color': '#888', 'padding': '4px'}),
], style={'background': '#f5f0e8', 'minHeight': '100vh'})


# ============================================================================
# CALLBACKS
# ============================================================================

# ---- Status bar -----------------------------------------------------------
@app.callback(
    Output('status', 'children'),
    Input('tick', 'n_intervals'))
def update_status(n):
    if not manager.backfill_complete:
        return html.Span(
            f"⏳ Initializing… {manager.backfill_progress}%",
            style={'color': '#aa6600'})
    st = price_feed.get_status()
    am_data = manager.get_am_data()
    tradable = sum(1 for d in am_data if d.get('is_tradable'))
    corr_count = sum(
        1 for v in config.correlation_data.values()
        if v.get('corr_at_earnings') is not None)
    decorr_count = sum(
        1 for v in config.correlation_data.values()
        if (v.get('decorrelation_score') or 0) > 0.3)
    msi_flag = "✅" if msi_engine.data_fetched else "⏳"
    if st['connected'] == 0:
        return html.Span(
            f"🔴 Connecting… | {tradable} tradable",
            style={'color': '#aa6600'})
    return html.Span(
        f"🟢 LIVE {st['connected']}/{st['total']} | "
        f"📨 {st['messages']:,} msgs | "
        f"📊 {len(config.fundamental_slopes)} fundamentals | "
        f"🔗 {corr_count} correlations "
        f"({decorr_count} decorrelating) | "
        f"🌐 MSI {msi_flag} | "
        f"🎯 {tradable} tradable",
        style={'color': '#1a5c2a'})


# ---- MSI Panel ------------------------------------------------------------
@app.callback(
    [Output('msi-kpis', 'children'),
     Output('msi-chart', 'figure'),
     Output('msi-components', 'children')],
    [Input('msi-tick', 'n_intervals'),
     Input('msi-lookback', 'value'),
     Input('msi-threshold', 'value')])
def update_msi_panel(n, lookback, threshold):
    empty_fig = go.Figure()
    empty_fig.update_layout(
        margin=dict(l=40, r=20, t=10, b=30),
        paper_bgcolor='#faf7f0', plot_bgcolor='#faf7f0',
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        annotations=[dict(
            text="⏳ Loading MSI data…", x=0.5, y=0.5,
            xref="paper", yref="paper", showarrow=False,
            font=dict(size=14, color="#888"))])
    empty_kpi = html.Span("Loading…",
                          style={'fontSize': '10px', 'color': '#888'})
    empty_comp = html.Span("")

    if not msi_engine.data_fetched:
        return empty_kpi, empty_fig, empty_comp

    lookback = lookback or _default_lookback
    threshold = threshold or _default_threshold

    # Compute historical MSI
    history = msi_engine.compute(threshold, lookback)
    if not history:
        return empty_kpi, empty_fig, empty_comp

    # Live estimate
    live_prices = price_feed.get_prices()
    live = msi_engine.live_estimate(live_prices, threshold, lookback)

    # --------------- KPI row -----------------------------------------------
    latest = live if live else history[-1]
    msi_val = latest['msi']
    breadth = latest['breadth']
    peak = latest['peak']
    disp = latest['dispersion']
    n_stocks = latest['num_stocks']

    # 5-day trend
    trend_arrow = "—"
    if len(history) >= 6:
        recent = [h['msi'] for h in history[-5:]]
        older = [h['msi'] for h in history[-10:-5]] if len(
            history) >= 10 else [h['msi'] for h in history[:5]]
        diff = np.mean(recent) - np.mean(older)
        if diff > 0.3:
            trend_arrow = "📈 Rising"
        elif diff < -0.3:
            trend_arrow = "📉 Falling"
        else:
            trend_arrow = "➡️ Stable"

    # Zone label
    if msi_val >= 5:
        zone = ("🟢 HIGH STASIS", "#1a8c3a")
    elif msi_val >= 3:
        zone = ("🟡 MODERATE", "#cc8800")
    else:
        zone = ("🔴 LOW / TRENDING", "#cc2200")

    kpi_row = html.Div([
        html.Div([
            html.Div(f"{msi_val:.2f}", className="msi-kpi-val"),
            html.Div("MSI LEVEL", className="msi-kpi-lbl"),
        ], className="msi-kpi"),
        html.Div([
            html.Div(f"{breadth:.0f}%", className="msi-kpi-val",
                     style={'color': '#0055aa'}),
            html.Div("BREADTH (≥3)", className="msi-kpi-lbl"),
        ], className="msi-kpi"),
        html.Div([
            html.Div(str(peak), className="msi-kpi-val",
                     style={'color': '#e65100'}),
            html.Div("PEAK", className="msi-kpi-lbl"),
        ], className="msi-kpi"),
        html.Div([
            html.Div(f"{disp:.2f}", className="msi-kpi-val",
                     style={'color': '#666'}),
            html.Div("DISPERSION", className="msi-kpi-lbl"),
        ], className="msi-kpi"),
        html.Div([
            html.Div(trend_arrow, style={
                'fontSize': '13px', 'fontWeight': '600'}),
            html.Div("5-DAY TREND", className="msi-kpi-lbl"),
        ], className="msi-kpi"),
        html.Div([
            html.Div(zone[0], style={
                'fontSize': '12px', 'fontWeight': '700',
                'color': zone[1]}),
            html.Div("ZONE", className="msi-kpi-lbl"),
        ], className="msi-kpi"),
    ])

    # --------------- Chart -------------------------------------------------
    dates = [h['date'] for h in history]
    msi_vals = [h['msi'] for h in history]
    breadth_vals = [h['breadth'] for h in history]
    disp_vals = [h['dispersion'] for h in history]

    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        row_heights=[0.7, 0.3],
        vertical_spacing=0.06)

    # --- Background zone shading on row 1 ---
    fig.add_hrect(
        y0=5, y1=20, fillcolor="rgba(26,140,58,0.08)",
        line_width=0, row=1, col=1)
    fig.add_hrect(
        y0=3, y1=5, fillcolor="rgba(204,136,0,0.06)",
        line_width=0, row=1, col=1)
    fig.add_hrect(
        y0=0, y1=3, fillcolor="rgba(204,34,0,0.05)",
        line_width=0, row=1, col=1)

    # MSI line
    fig.add_trace(go.Scatter(
        x=dates, y=msi_vals,
        mode='lines', name='MSI',
        line=dict(color='#1a5c2a', width=2.5),
        fill='tozeroy',
        fillcolor='rgba(26,92,42,0.10)'),
        row=1, col=1)

    # Zone reference lines
    fig.add_hline(y=5, line_dash="dot",
                  line_color="rgba(26,140,58,0.4)",
                  annotation_text="High",
                  annotation_position="top left",
                  annotation_font_size=8,
                  row=1, col=1)
    fig.add_hline(y=3, line_dash="dot",
                  line_color="rgba(204,136,0,0.4)",
                  annotation_text="Moderate",
                  annotation_position="top left",
                  annotation_font_size=8,
                  row=1, col=1)

    # Live MSI point
    if live:
        fig.add_trace(go.Scatter(
            x=[live['date']], y=[live['msi']],
            mode='markers', name='Live',
            marker=dict(color='#e65100', size=10,
                        symbol='diamond',
                        line=dict(width=2, color='#fff'))),
            row=1, col=1)

    # Breadth bars on row 2
    bar_colors = ['#1a8c3a' if b >= 60
                  else '#cc8800' if b >= 30
                  else '#cc2200'
                  for b in breadth_vals]
    fig.add_trace(go.Bar(
        x=dates, y=breadth_vals, name='Breadth %',
        marker_color=bar_colors, opacity=0.7),
        row=2, col=1)
    fig.add_hline(y=50, line_dash="dot",
                  line_color="rgba(0,0,0,0.2)", row=2, col=1)

    fig.update_layout(
        margin=dict(l=45, r=15, t=8, b=25),
        paper_bgcolor='#faf7f0',
        plot_bgcolor='#faf7f0',
        showlegend=False,
        font=dict(family='Consolas, monospace', size=9),
        hovermode='x unified')
    fig.update_yaxes(title_text="MSI", row=1, col=1,
                     gridcolor='rgba(0,0,0,0.06)')
    fig.update_yaxes(title_text="Breadth %", row=2, col=1,
                     range=[0, 105],
                     gridcolor='rgba(0,0,0,0.06)')
    fig.update_xaxes(gridcolor='rgba(0,0,0,0.06)')

    # --------------- Component table ---------------------------------------
    comp = latest.get('components', {})
    if comp:
        sym_items = sorted(comp.items(),
                           key=lambda x: x[1], reverse=True)
        comp_cells = []
        for sym, stasis in sym_items:
            if stasis >= 5:
                bg = '#c8e6c9'
            elif stasis >= 3:
                bg = '#fff9c4'
            else:
                bg = '#ffcdd2'
            comp_cells.append(
                html.Span(
                    f"{sym}:{stasis}",
                    style={
                        'fontSize': '9px',
                        'fontFamily': 'Consolas, monospace',
                        'fontWeight': '600',
                        'background': bg,
                        'padding': '2px 6px',
                        'borderRadius': '3px',
                        'margin': '2px',
                        'display': 'inline-block'}))
        comp_div = html.Div([
            html.Span("COMPONENTS: ",
                      style={'fontSize': '9px', 'fontWeight': '700',
                             'color': '#333', 'marginRight': '6px'}),
            *comp_cells
        ])
    else:
        comp_div = html.Span("")

    return kpi_row, fig, comp_div


# ---- Filter toggle --------------------------------------------------------
@app.callback(
    [Output('f-all', 'active'), Output('f-trad', 'active'),
     Output('f-decorr', 'active'), Output('fmode', 'data')],
    [Input('f-all', 'n_clicks'), Input('f-trad', 'n_clicks'),
     Input('f-decorr', 'n_clicks')],
    prevent_initial_call=True)
def toggle_filter(n1, n2, n3):
    ctx = callback_context
    tid = ctx.triggered[0]['prop_id']
    if 'f-all' in tid:
        return True, False, False, 'all'
    elif 'f-decorr' in tid:
        return False, False, True, 'decorr'
    return False, True, False, 'tradable'


# ---- Main AM table --------------------------------------------------------
@app.callback(
    Output('tbl', 'data'),
    [Input('tick', 'n_intervals'), Input('fmode', 'data'),
     Input('f-dir', 'value'), Input('f-sort', 'value')])
def update_table(n, fm, fd, fs):
    if not manager.backfill_complete:
        return []
    data = manager.get_am_data()
    if not data:
        return []
    rows = []
    for d in data:
        if fm == 'tradable' and not d.get('is_tradable'):
            continue
        if fm == 'decorr':
            cd = d.get('corr_details', {})
            dcor = cd.get('decor_score')
            if dcor is None or dcor < 0.15:
                continue
        if fd != 'ALL' and d.get('direction') != fd:
            continue
        sd = d.get('slope_details', {})
        cd = d.get('corr_details', {})
        w52 = d.get('week52_percentile')
        corr_at_e = cd.get('corr_at_earnings')
        corr_now = cd.get('corr_now')
        corr_delta = cd.get('corr_delta')
        decor_score = cd.get('decor_score')
        divergence = cd.get('divergence')
        div_display = '—'
        if divergence == 'PRICE_AHEAD':
            div_display = 'P>R'
        elif divergence == 'PRICE_BEHIND':
            div_display = 'P<R'
        elif divergence == 'ALIGNED':
            div_display = '≈'
        rows.append({
            '✓': '✅' if d.get('is_tradable') else '',
            'SYM': d['symbol'],
            'BAND': f"{d['threshold_pct']:.2f}%",
            'STS': d['stasis'],
            'DIR': d.get('direction') or '—',
            'SMS': d.get('sms', 0),
            'FMS': d.get('fms', 0),
            'CMS': d.get('cms', 0),
            'TMS': d.get('tms', 0),
            'C@E': fmt_corr(corr_at_e),
            'C@N': fmt_corr(corr_now),
            'ΔCOR': fmt_corr_delta(corr_delta),
            'DCOR': (f"{decor_score:.2f}"
                     if decor_score is not None else '—'),
            'DIV': div_display,
            'REV5': fmt_slope(sd.get('Rev_5')),
            'FCF5': fmt_slope(sd.get('FCF_5')),
            'FCFY': (f"{sd['FCFY']*100:.1f}%"
                     if sd.get('FCFY') else '—'),
            '52W': (f"{w52:.0f}%" if w52 is not None else '—'),
            'PRICE': (f"${d['current_price']:.2f}"
                      if d.get('current_price') else '—'),
            'TP': (f"${d['take_profit']:.2f}"
                   if d.get('take_profit') else '—'),
            'SL': (f"${d['stop_loss']:.2f}"
                   if d.get('stop_loss') else '—'),
            'R:R': fmt_rr(d.get('risk_reward')),
            'DUR': d.get('stasis_duration_str', '—'),
            '_tms': d.get('tms', 0),
            '_fms': d.get('fms', 0),
            '_cms': d.get('cms', 0),
            '_stasis': d['stasis'],
            '_52w': w52 if w52 is not None else 999,
            '_dcor_raw': (decor_score
                          if decor_score is not None else -1),
            '_corr_delta': (corr_delta
                            if corr_delta is not None else 999)})
    if not rows:
        return []
    df = pd.DataFrame(rows)
    sort_map = {
        'tms': ('_tms', False), 'fms': ('_fms', False),
        'cms': ('_cms', False), 'decorr': ('_dcor_raw', False),
        'corr_delta': ('_corr_delta', True),
        'stasis': ('_stasis', False), '52w': ('_52w', True)}
    col, asc = sort_map.get(fs, ('_tms', False))
    df = df.sort_values(col, ascending=asc).head(200)
    df = df.drop(columns=[
        '_tms', '_fms', '_cms', '_stasis', '_52w',
        '_dcor_raw', '_corr_delta'], errors='ignore')
    return df.to_dict('records')


# ============================================================================
# API ENDPOINTS
# ============================================================================
@server.route('/api/health')
def health():
    return json.dumps({
        'status': 'ok', 'app': 'stasis_am',
        'initialized': manager.initialized,
        'backfill_complete': manager.backfill_complete,
        'backfill_progress': manager.backfill_progress,
        'msi_data_fetched': msi_engine.data_fetched,
        'correlations_calculated': sum(
            1 for v in config.correlation_data.values()
            if v.get('corr_at_earnings') is not None)})


@server.route('/api/correlations')
def api_correlations():
    result = {}
    for sym, data in config.correlation_data.items():
        if data.get('corr_at_earnings') is not None:
            result[sym] = {
                'corr_at_earnings': data['corr_at_earnings'],
                'corr_now': data.get('corr_now'),
                'corr_delta': data.get('corr_delta'),
                'decorrelation_score': data.get('decorrelation_score'),
                'divergence': data.get('price_vs_rev_divergence'),
                'earnings_date_price': data.get('earnings_date_price'),
                'current_price': data.get('current_price'),
                'price_change_since_earnings_pct': data.get(
                    'price_change_since_earnings_pct'),
                'latest_rev_change_pct': data.get(
                    'latest_rev_change_pct'),
                'aligned_quarters': data.get('aligned_count')}
    return json.dumps(result, indent=2)


@server.route('/api/decorrelating')
def api_decorrelating():
    items = []
    for sym, data in config.correlation_data.items():
        if data.get('decorrelation_score') is not None:
            items.append({
                'symbol': sym,
                'decorrelation_score': data['decorrelation_score'],
                'corr_at_earnings': data.get('corr_at_earnings'),
                'corr_now': data.get('corr_now'),
                'corr_delta': data.get('corr_delta'),
                'divergence': data.get('price_vs_rev_divergence')})
    items.sort(key=lambda x: x['decorrelation_score'], reverse=True)
    return json.dumps(items, indent=2)


@server.route('/api/msi')
def api_msi():
    """Return full MSI history for default params."""
    history = msi_engine.compute(
        config.msi_default_threshold,
        config.msi_default_lookback)
    out = []
    for h in history:
        out.append({
            'date': h['date'], 'msi': h['msi'],
            'breadth': h['breadth'], 'peak': h['peak'],
            'dispersion': h['dispersion'],
            'num_stocks': h['num_stocks'],
            'components': h['components']})
    return json.dumps(out, indent=2)


# ============================================================================
# INITIALIZATION
# ============================================================================
_init_done = False
_init_lock = threading.Lock()


def initialize():
    global _init_done
    with _init_lock:
        if _init_done:
            return
        print("=" * 70)
        print("   STASIS AM SERVER  +  MARKET STASIS INDEX")
        print("   © 2026 Truth Communications LLC")
        print("=" * 70)
        print(f"\n🎯 Symbols: {len(config.symbols)}")
        print(f"🌐 MSI Sample: {config.msi_sample_symbols}")

        config.week52_data = fetch_52_week_data()
        config.volumes = fetch_volume_data()

        # ---- MSI daily data fetch (before long blocking steps) ----
        msi_engine.fetch_data(max_calendar_days=400)

        # Pre-compute MSI for all standard lookback/threshold combos
        if msi_engine.data_fetched:
            print("📈 MSI — Pre-computing for all parameter combos…")
            for th in config.msi_threshold_options:
                for lb in config.msi_lookback_options:
                    msi_engine.compute(th, lb)
            print("✅ MSI pre-computation done\n")

        fetch_all_fundamental_data()
        calculate_all_correlations()
        manager.backfill()
        price_feed.start()
        manager.start()

        corr_ok = sum(
            1 for v in config.correlation_data.values()
            if v.get('corr_at_earnings') is not None)
        decorr = sum(
            1 for v in config.correlation_data.values()
            if (v.get('decorrelation_score') or 0) > 0.3)

        print(f"\n✅ READY")
        print(f"  📊 {len(config.fundamental_slopes)} fundamentals")
        print(f"  🔗 {corr_ok} correlations calculated")
        print(f"  🔔 {decorr} significantly decorrelating")
        print(f"  🌐 MSI data: {msi_engine.data_fetched}")
        print("=" * 70)
        _init_done = True


_init_thread = threading.Thread(target=initialize, daemon=True)
_init_thread.start()


# ============================================================================
# MAIN
# ============================================================================
if __name__ == '__main__':
    _init_thread.join()
    port = int(os.environ.get('PORT', 8050))
    print(f"\n🟢 http://0.0.0.0:{port}\n")
    app.run(debug=False, host='0.0.0.0', port=port)
