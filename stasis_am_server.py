# -*- coding: utf-8 -*-
"""
Created on Sat Feb  7 12:25:45 2026

@author: brcum
"""

# -*- coding: utf-8 -*-
"""
STASIS AM SERVER v2.1
Standalone web server for Stasis AM - Alpha Markets
Deploy to: stasisAM.beyondpriceandtime.com
Copyright © 2026 Truth Communications LLC. All Rights Reserved.
"""

import sys
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
import signal
import traceback

import dash
from dash import dcc, html, Input, Output, State, callback_context, no_update, dash_table
import dash_bootstrap_components as dbc
import pandas as pd
import websocket
import ssl
import requests

# ============================================================================
# API KEYS & SERVER CONFIG
# ============================================================================

POLYGON_API_KEY = os.environ.get("POLYGON_API_KEY", "PnzhJOXEJO7tSpHr0ct2zjFKi6XO0yGi")
PORT = int(os.environ.get("PORT", 8050))
HOST = os.environ.get("HOST", "0.0.0.0")

# CORS origin for desktop app and PM server communication
ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "*")

# PM server URL for cross-communication (if needed)
PM_SERVER_URL = os.environ.get("PM_SERVER_URL", "https://stasisPM.beyondpriceandtime.com")

# ============================================================================
# CONFIGURATION
# ============================================================================


@dataclass
class Config:
    symbols: List[str] = field(default_factory=lambda: [
        "SPY", "QQQ", "IWM", "DIA", "XLF", "XLE", "XLU", "XLK",
        "XLP", "XLB", "XLV", "XLI", "XLY", "XLC", "XLRE", "KRE",
        "SMH", "XBI", "GDX",
        'AAPL', 'MSFT', 'GOOGL', 'GOOG', 'AMZN', 'NVDA', 'META',
        'TSLA', 'AVGO', 'ORCL', 'ADBE', 'CRM', 'AMD', 'INTC'
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
        0.005, 0.0075, 0.01, 0.0125, 0.015, 0.02, 0.025,
        0.03, 0.04, 0.05
    ])

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
    min_tradable_stasis: int = 3


config = Config()
config.symbols = list(dict.fromkeys(config.symbols))

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
        return (p - self.start_price) / self.start_price * 100 if self.start_price else 0


# ============================================================================
# HELPER FUNCTIONS
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
    return "0:1" if rr <= 0 else (f"{rr:.2f}:1" if rr < 10 else f"{rr:.0f}:1")


def format_bits(bits):
    return "".join(str(b) for b in bits) if bits else "—"


def format_band(threshold_pct):
    if threshold_pct < 0.1:
        return f"{threshold_pct:.4f}%"
    elif threshold_pct < 1:
        return f"{threshold_pct:.3f}%"
    else:
        return f"{threshold_pct:.2f}%"


# ============================================================================
# FUNDAMENTAL DATA FUNCTIONS
# ============================================================================


def fetch_fundamental_data_polygon(sym):
    try:
        url = (f"{config.polygon_rest_url}/vX/reference/financials"
               f"?ticker={sym}&timeframe=quarterly&limit=24"
               f"&sort=filing_date&order=desc&apiKey={config.polygon_api_key}")
        resp = requests.get(url, timeout=30)
        if resp.status_code != 200:
            return None
        results = resp.json().get('results', [])
        if not results:
            return None
        fund = {k: [] for k in [
            'dates', 'revenue', 'net_income', 'operating_cash_flow',
            'capex', 'fcf', 'total_assets', 'total_liabilities',
            'shareholders_equity', 'current_assets', 'current_liabilities',
            'total_debt', 'eps'
        ]}
        for r in results:
            try:
                fi = r.get('financials', {})
                inc = fi.get('income_statement', {})
                cf = fi.get('cash_flow_statement', {})
                bs = fi.get('balance_sheet', {})
                rev = inc.get('revenues', {}).get('value', 0) or 0
                ni = inc.get('net_income_loss', {}).get('value', 0) or 0
                eps = inc.get('basic_earnings_per_share', {}).get('value', 0) or 0
                ocf = cf.get('net_cash_flow_from_operating_activities', {}).get('value', 0) or 0
                cx = cf.get('net_cash_flow_from_investing_activities', {}).get('value', 0) or 0
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
            except:
                continue
        for k in fund:
            fund[k] = fund[k][::-1]
        return fund
    except:
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
    except:
        pass
    try:
        if len(s.dropna()) >= 21:
            e = s.ewm(span=sl, adjust=False).mean()
            if abs(e.iloc[-21]) > 0.0001:
                s20 = (e.iloc[-1] - e.iloc[-21]) / abs(e.iloc[-21])
    except:
        pass
    return s5, s20


def calculate_all_slopes(fund, ratios):
    sl = {}
    sl['Rev_Slope_5'], sl['Rev_Slope_20'] = calculate_slopes(fund.get('revenue', []))
    sl['FCF_Slope_5'], sl['FCF_Slope_20'] = calculate_slopes(fund.get('fcf', []))
    for n, k in [('P/E Ratio', 'pe_ratio'), ('Return on Equity', 'roe'),
                 ('Net Profit Margin', 'net_profit_margin'),
                 ('Debt to Equity Ratio', 'debt_to_equity')]:
        sl[f'{n}_Slope_5'], sl[f'{n}_Slope_20'] = calculate_slopes(ratios.get(k, []))
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
                ratios = {k: [] for k in ['pe_ratio', 'roe', 'net_profit_margin',
                                           'debt_to_equity', 'fcfy']}
                for j in range(len(fund['revenue'])):
                    try:
                        eps = fund['eps'][j]
                        ratios['pe_ratio'].append(price / eps if eps > 0 else None)
                        eq_j = fund['shareholders_equity'][j]
                        ratios['roe'].append(fund['net_income'][j] / eq_j if eq_j > 0 else None)
                        rev_j = fund['revenue'][j]
                        ratios['net_profit_margin'].append(
                            fund['net_income'][j] / rev_j if rev_j else None)
                        ratios['debt_to_equity'].append(
                            fund['total_debt'][j] / eq_j if eq_j > 0 else None)
                        if j >= 3:
                            ratios['fcfy'].append(
                                sum(fund['fcf'][max(0, j - 3):j + 1]) / mcap if mcap else None)
                        else:
                            ratios['fcfy'].append(None)
                    except:
                        for k in ratios:
                            ratios[k].append(None)
                slopes = calculate_all_slopes(fund, ratios)
                config.fundamental_data[sym] = fund
                config.fundamental_slopes[sym] = slopes
                ok += 1
            else:
                fail += 1
        except:
            fail += 1
        if (i + 1) % 25 == 0:
            print(f"   📈 {i + 1}/{len(config.symbols)} (✓{ok} ✗{fail})")
        time.sleep(0.15)
    print(f"✅ Fundamentals: {ok} ok, {fail} failed\n")


def calculate_stasis_merit_score(snap):
    ms = 0
    st = snap.get('stasis', 0)
    for t, p in [(15, 10), (12, 9), (10, 8), (8, 7), (7, 6),
                 (6, 5), (5, 4), (4, 3), (3, 2), (2, 1)]:
        if st >= t:
            ms += p
            break
    rr = snap.get('risk_reward')
    if rr:
        for t, p in [(3, 5), (2.5, 4), (2, 3), (1.5, 2), (1, 1)]:
            if rr >= t:
                ms += p
                break
    ms += {'VERY_STRONG': 4, 'STRONG': 3, 'MODERATE': 2, 'WEAK': 1}.get(
        snap.get('signal_strength', ''), 0)
    dur = snap.get('duration_seconds', 0)
    if dur >= 3600:
        ms += 3
    elif dur >= 1800:
        ms += 2
    elif dur >= 900:
        ms += 1
    return ms


def calculate_fundamental_merit_score(symbol, w52_pct):
    ms = 0
    sd = {}
    slopes = config.fundamental_slopes.get(symbol, {})
    if not slopes:
        if w52_pct is not None:
            for t, p in [(5, 8), (15, 7), (25, 6), (35, 5), (45, 4),
                         (55, 3), (65, 2), (75, 1)]:
                if w52_pct <= t:
                    ms += p
                    break
        return ms, sd
    for lbl, key, tps in [
        ('Rev_5', 'Rev_Slope_5', [(0.30, 4), (0.20, 3), (0.10, 2), (0.05, 1)]),
        ('FCF_5', 'FCF_Slope_5', [(0.40, 4), (0.25, 3), (0.10, 2), (0.05, 1)]),
        ('ROE_5', 'Return on Equity_Slope_5', [(0.20, 2), (0.10, 1)]),
        ('NPM_5', 'Net Profit Margin_Slope_5', [(0.20, 2), (0.10, 1)])]:
        v = slopes.get(key)
        sd[lbl] = v
        if v is not None:
            for t, p in tps:
                if v >= t:
                    ms += p
                    break
    for lbl, key, tps in [
        ('PE_5', 'P/E Ratio_Slope_5', [(-0.25, 3), (-0.15, 2), (-0.05, 1)]),
        ('DE_5', 'Debt to Equity Ratio_Slope_5', [(-0.20, 2), (-0.10, 1)])]:
        v = slopes.get(key)
        sd[lbl] = v
        if v is not None:
            for t, p in tps:
                if v <= t:
                    ms += p
                    break
    if w52_pct is not None:
        for t, p in [(5, 8), (15, 7), (25, 6), (35, 5), (45, 4),
                     (55, 3), (65, 2), (75, 1)]:
            if w52_pct <= t:
                ms += p
                break
    fcfy = slopes.get('FCFY')
    sd['FCFY'] = fcfy
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
    w52 = {}
    end = datetime.now()
    start = end - timedelta(days=365)
    ok = fail = 0
    for i, sym in enumerate(config.symbols):
        try:
            url = (f"{config.polygon_rest_url}/v2/aggs/ticker/{sym}/range/1/day/"
                   f"{start.strftime('%Y-%m-%d')}/{end.strftime('%Y-%m-%d')}"
                   f"?adjusted=true&sort=asc&limit=365&apiKey={config.polygon_api_key}")
            r = requests.get(url, timeout=15)
            if r.status_code == 200:
                d = r.json()
                res = d.get('results', [])
                if res:
                    hv = max(b['h'] for b in res)
                    lv = min(b['l'] for b in res)
                    w52[sym] = {'high': hv, 'low': lv, 'range': hv - lv,
                                'current': res[-1]['c']}
                    ok += 1
                else:
                    w52[sym] = {'high': None, 'low': None, 'range': None, 'current': None}
                    fail += 1
            else:
                w52[sym] = {'high': None, 'low': None, 'range': None, 'current': None}
                fail += 1
            if (i + 1) % 50 == 0:
                print(f"   52W: {i + 1}/{len(config.symbols)} (✓{ok} ✗{fail})")
            time.sleep(0.13)
        except:
            w52[sym] = {'high': None, 'low': None, 'range': None, 'current': None}
            fail += 1
    print(f"✅ 52-week: {ok} ok, {fail} failed\n")
    return w52


def fetch_volume_data():
    print("📊 Fetching volume data...")
    vols = {}
    end = datetime.now()
    start = end - timedelta(days=45)
    for i, sym in enumerate(config.symbols):
        try:
            url = (f"{config.polygon_rest_url}/v2/aggs/ticker/{sym}/range/1/day/"
                   f"{start.strftime('%Y-%m-%d')}/{end.strftime('%Y-%m-%d')}"
                   f"?adjusted=true&sort=desc&limit=30&apiKey={config.polygon_api_key}")
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                res = r.json().get('results', [])
                if res:
                    vols[sym] = (sum(b['v'] for b in res) / len(res)) / 1e6
                else:
                    vols[sym] = 10.0
            else:
                vols[sym] = 10.0
            if (i + 1) % 50 == 0:
                print(f"   Vol: {i + 1}/{len(config.symbols)}")
            time.sleep(0.13)
        except:
            vols[sym] = 10.0
    print("✅ Volume loaded\n")
    return vols


def fetch_historical_bars(sym, days=5):
    bars = []
    end = datetime.now()
    start = end - timedelta(days=days)
    try:
        url = (f"{config.polygon_rest_url}/v2/aggs/ticker/{sym}/range/1/minute/"
               f"{start.strftime('%Y-%m-%d')}/{end.strftime('%Y-%m-%d')}"
               f"?adjusted=true&sort=asc&limit=50000&apiKey={config.polygon_api_key}")
        r = requests.get(url, timeout=30)
        if r.status_code == 200:
            res = r.json().get('results', [])
            bars = [{'timestamp': datetime.fromtimestamp(b['t'] / 1000), 'close': b['c']}
                    for b in res]
    except:
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
        bl = list(self.bits)
        sc = 1
        si = len(bl) - 1
        for i in range(len(bl) - 1, 0, -1):
            if bl[i].bit != bl[i - 1].bit:
                sc += 1
                si = i - 1
            else:
                break
        prev = self.current_stasis
        self.current_stasis = sc
        self.last_bit = bl[-1].bit
        if prev < 2 and sc >= 2 and 0 <= si < len(bl):
            self.stasis_info = StasisInfo(bl[si].timestamp, bl[si].price, sc)
        elif sc >= 2 and self.stasis_info and sc > self.stasis_info.peak_stasis:
            self.stasis_info.peak_stasis = sc
        elif prev >= 2 and sc < 2:
            self.stasis_info = None
        if sc >= 2:
            self.direction = Direction.LONG if self.last_bit == 1 else Direction.SHORT
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
            self.direction = None
            self.signal_strength = None

    def get_snapshot(self, live_price=None):
        with self._lock:
            p = live_price if live_price is not None else self.current_live_price
            si = self.stasis_info
            tp = sl = rr = None
            distance_to_tp_pct = None
            distance_to_sl_pct = None
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
                else:
                    rr = None
                if p > 0:
                    distance_to_tp_pct = (abs(tp - p) / p) * 100
                    distance_to_sl_pct = (abs(sl - p) / p) * 100

            recent_bits = [b.bit for b in list(self.bits)[-15:]]

            return {
                'symbol': self.symbol,
                'is_etf': self.is_etf,
                'threshold': self.threshold,
                'threshold_pct': self.threshold * 100,
                'stasis': self.current_stasis,
                'total_bits': self.total_bits,
                'recent_bits': recent_bits,
                'current_price': p,
                'anchor_price': si.start_price if si else None,
                'direction': self.direction.value if self.direction else None,
                'signal_strength': self.signal_strength.value if self.signal_strength else None,
                'is_tradable': (self.current_stasis >= config.min_tradable_stasis
                                and self.direction is not None and self.volume > 1.0),
                'stasis_start_str': si.get_start_date_str() if si else "—",
                'stasis_duration_str': si.get_duration_str() if si else "—",
                'duration_seconds': si.get_duration().total_seconds() if si else 0,
                'stasis_price_change_pct': stasis_price_change_pct,
                'take_profit': tp,
                'stop_loss': sl,
                'risk_reward': rr,
                'distance_to_tp_pct': distance_to_tp_pct,
                'distance_to_sl_pct': distance_to_sl_pct,
                'week52_percentile': calculate_52week_percentile(p, self.symbol),
                'volume': self.volume,
            }


# ============================================================================
# PRICE FEED
# ============================================================================


class PolygonPriceFeed:
    def __init__(self):
        self.lock = threading.Lock()
        self.current_prices = {s: None for s in config.symbols}
        self.is_running = False
        self.ws = None
        self.message_count = 0

    def start(self):
        self.is_running = True
        threading.Thread(target=self._loop, daemon=True).start()
        print("🔌 WebSocket starting...")

    def _loop(self):
        while self.is_running:
            try:
                self._connect()
            except Exception as e:
                print(f"WS reconnect err: {e}")
                time.sleep(5)

    def _connect(self):
        def on_msg(ws, raw):
            try:
                data = json.loads(raw)
                if isinstance(data, list):
                    for m in data:
                        self._proc(m)
                else:
                    self._proc(data)
            except:
                pass

        def on_open(ws):
            print("✅ WS connected, authenticating...")
            ws.send(json.dumps({"action": "auth", "params": config.polygon_api_key}))

        def on_error(ws, err):
            print(f"WS error: {err}")

        self.ws = websocket.WebSocketApp(
            config.polygon_ws_url,
            on_open=on_open, on_message=on_msg, on_error=on_error
        )
        self.ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})

    def _proc(self, msg):
        ev = msg.get('ev')
        if ev == 'status':
            status = msg.get('status', '')
            print(f"   WS status: {status} - {msg.get('message', '')}")
            if status == 'auth_success':
                self._subscribe()
            elif status == 'auth_failed':
                print("   ❌ AUTH FAILED — check API key")
        elif ev in ('A', 'AM', 'T', 'Q'):
            sym = msg.get('sym', '') or msg.get('S', '')
            price = msg.get('c') or msg.get('vw') or msg.get('p') or msg.get('bp')
            if price and sym in self.current_prices:
                with self.lock:
                    self.current_prices[sym] = float(price)
                    self.message_count += 1

    def _subscribe(self):
        syms = list(config.symbols)
        for i in range(0, len(syms), 50):
            batch = syms[i:i + 50]
            self.ws.send(json.dumps({
                "action": "subscribe",
                "params": ",".join(f"A.{s}" for s in batch)
            }))
            time.sleep(0.1)
        print(f"📡 Subscribed to {len(syms)} symbols")

    def get_prices(self):
        with self.lock:
            return {k: v for k, v in self.current_prices.items() if v is not None}

    def get_status(self):
        with self.lock:
            return {
                'connected': sum(1 for v in self.current_prices.values() if v is not None),
                'total': len(config.symbols),
                'messages': self.message_count
            }


price_feed = PolygonPriceFeed()

# ============================================================================
# BITSTREAM MANAGER (AM-only version)
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
        self.stream_count = 0
        self.tradable_count = 0

    def backfill(self):
        print("\n" + "=" * 60 + "\n📜 BACKFILLING HISTORICAL DATA\n" + "=" * 60)
        hist = {}
        for i, sym in enumerate(config.symbols):
            bars = fetch_historical_bars(sym, config.history_days)
            if bars:
                hist[sym] = bars
            self.backfill_progress = int((i + 1) / len(config.symbols) * 100)
            if (i + 1) % 25 == 0:
                print(f"   📊 {i + 1}/{len(config.symbols)} ({self.backfill_progress}%)"
                      f" — {len(hist)} with data")
            time.sleep(0.13)

        print(f"\n   Building bitstreams from {len(hist)} symbols...")
        with self.lock:
            for sym, bars in hist.items():
                if not bars or len(bars) < 2:
                    continue
                vol = config.volumes.get(sym, 10.0)
                for th in config.thresholds:
                    key = (sym, th)
                    self.streams[key] = Bitstream(sym, th, bars[0]['close'], vol)
                    for bar in bars:
                        self.streams[key].process_price(bar['close'], bar['timestamp'])

        self.stream_count = len(self.streams)
        self.tradable_count = sum(1 for s in self.streams.values()
                                  if s.current_stasis >= config.min_tradable_stasis
                                  and s.direction is not None and s.volume > 1.0)
        self.initialized = True
        self.backfill_complete = True
        print(f"✅ Streams: {self.stream_count} | Tradable: {self.tradable_count}")
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
            prices = price_feed.get_prices()
            ts = datetime.now()
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
            prices = price_feed.get_prices()
            snaps = []
            with self.lock:
                for s in self.streams.values():
                    snaps.append(s.get_snapshot(prices.get(s.symbol)))

            am = self._build_am(snaps)
            self.tradable_count = sum(1 for s in am if s.get('is_tradable'))

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
            rows.append({**s, 'sms': sms, 'fms': fms, 'tms': sms + fms,
                         'slope_details': sd})
        return rows

    def get_am_data(self):
        with self.cache_lock:
            return copy.deepcopy(self.cached_am_data)


manager = BitstreamManager()

# ============================================================================
# SELECTED SYMBOL STATE (for cross-app communication)
# ============================================================================

_selected_symbol = {'symbol': None, 'lock': threading.Lock()}


def set_selected_symbol(sym):
    with _selected_symbol['lock']:
        _selected_symbol['symbol'] = sym


def get_selected_symbol():
    with _selected_symbol['lock']:
        return _selected_symbol['symbol']


# ============================================================================
# DASH AM APP
# ============================================================================

app = dash.Dash(
    __name__,
    suppress_callback_exceptions=True,
    external_stylesheets=[dbc.themes.FLATLY],
    title="STASIS AM",
)

server = app.server  # Flask server for Railway/Gunicorn

# Add CORS headers
@server.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', ALLOWED_ORIGINS)
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response


app.layout = html.Div([
    dcc.Store(id='fmode', data='tradable'),
    dcc.Interval(id='tick', interval=1000, n_intervals=0),
    html.Div(id='status', style={'fontSize': '10px', 'padding': '6px',
                                  'background': '#e8f5e9', 'fontWeight': 'bold'}),
    html.Div([
        dbc.ButtonGroup([
            dbc.Button("ALL", id="f-all", size="sm", outline=True,
                       style={'fontSize': '9px'}),
            dbc.Button("TRADABLE", id="f-trad", size="sm", outline=True, active=True,
                       style={'fontSize': '9px', 'color': '#1a5c2a'}),
        ], size="sm", className="me-2"),
        dcc.Dropdown(id='f-dir',
                     options=[{'label': x, 'value': x} for x in ['ALL', 'LONG', 'SHORT']],
                     value='ALL', clearable=False,
                     style={'width': '80px', 'fontSize': '10px',
                            'display': 'inline-block'}),
        dcc.Dropdown(id='f-sort', options=[
            {'label': 'TMS ↓', 'value': 'tms'},
            {'label': 'FMS ↓', 'value': 'fms'},
            {'label': 'STASIS ↓', 'value': 'stasis'},
            {'label': '52W ↑', 'value': '52w'}],
            value='tms', clearable=False,
            style={'width': '90px', 'fontSize': '10px',
                   'display': 'inline-block', 'marginLeft': '4px'}),
    ], className="d-flex align-items-center p-1",
        style={'background': '#f5f0e8'}),
    html.Div("💡 Click any row → Desktop app navigates SA, RH & TT to that stock",
             style={'fontSize': '9px', 'color': '#aa6600', 'padding': '2px 6px',
                    'background': '#f5f0e8'}),
    dash_table.DataTable(
        id='tbl', row_selectable='single',
        columns=[{'name': c, 'id': c} for c in [
            '✓', 'SYM', 'BAND', 'STS', 'DIR', 'SMS', 'FMS', 'TMS',
            'REV5', 'FCF5', 'FCFY', '52W', 'PRICE', 'TP', 'SL', 'R:R', 'DUR']],
        sort_action='native',
        style_table={'overflowY': 'auto'},
        style_cell={
            'backgroundColor': '#faf7f0', 'color': '#1a1a1a',
            'padding': '3px 4px', 'fontSize': '10px',
            'fontFamily': 'Consolas, monospace', 'whiteSpace': 'nowrap',
            'textAlign': 'right', 'border': '1px solid #ddd'
        },
        style_cell_conditional=[
            {'if': {'column_id': 'SYM'}, 'textAlign': 'left',
             'fontWeight': '700', 'color': '#1a5c2a'},
            {'if': {'column_id': 'DIR'}, 'textAlign': 'center'},
        ],
        style_header={
            'backgroundColor': '#1a5c2a', 'color': '#fff',
            'fontWeight': '700', 'fontSize': '9px', 'textAlign': 'center'
        },
        style_data_conditional=[
            {'if': {'filter_query': '{DIR} = "LONG"', 'column_id': 'DIR'},
             'color': '#1a8c3a', 'fontWeight': 'bold'},
            {'if': {'filter_query': '{DIR} = "SHORT"', 'column_id': 'DIR'},
             'color': '#cc2200', 'fontWeight': 'bold'},
            {'if': {'filter_query': '{STS} >= 10'}, 'backgroundColor': '#e8f5e9'},
            {'if': {'filter_query': '{STS} >= 7 && {STS} < 10'},
             'backgroundColor': '#f1f8e9'},
            {'if': {'column_id': 'PRICE'}, 'color': '#0055aa', 'fontWeight': '600'},
            {'if': {'column_id': 'TP'}, 'color': '#1a8c3a'},
            {'if': {'column_id': 'SL'}, 'color': '#cc2200'},
            {'if': {'filter_query': '{TMS} >= 30', 'column_id': 'TMS'},
             'backgroundColor': '#1a8c3a', 'color': '#fff'},
            {'if': {'filter_query': '{TMS} >= 20 && {TMS} < 30', 'column_id': 'TMS'},
             'backgroundColor': '#4caf50', 'color': '#fff'},
            {'if': {'row_index': 'odd'}, 'backgroundColor': '#f0ebe0'},
        ]),
], style={'background': '#f5f0e8', 'minHeight': '100vh'})


@app.callback(Output('status', 'children'), Input('tick', 'n_intervals'))
def am_status(n):
    if not manager.backfill_complete:
        return html.Span(f"⏳ Initializing... {manager.backfill_progress}%",
                         style={'color': '#aa6600'})
    st = price_feed.get_status()
    am_data = manager.get_am_data()
    tradable = sum(1 for d in am_data if d.get('is_tradable'))
    total = len(am_data)
    if st['connected'] == 0:
        return html.Span(
            f"🔴 Connecting... | {total} streams | {tradable} tradable",
            style={'color': '#aa6600'})
    return html.Span(
        f"🟢 LIVE {st['connected']}/{st['total']} | "
        f"📨 {st['messages']:,} msgs | "
        f"📊 {len(config.fundamental_slopes)} fundamentals | "
        f"🎯 {tradable} tradable signals",
        style={'color': '#1a5c2a'}
    )


@app.callback(
    [Output('f-all', 'active'), Output('f-trad', 'active'), Output('fmode', 'data')],
    [Input('f-all', 'n_clicks'), Input('f-trad', 'n_clicks')],
    prevent_initial_call=True)
def am_filter(n1, n2):
    ctx = callback_context
    if 'f-all' in ctx.triggered[0]['prop_id']:
        return True, False, 'all'
    return False, True, 'tradable'


@app.callback(
    Output('tbl', 'data'),
    [Input('tick', 'n_intervals'), Input('fmode', 'data'),
     Input('f-dir', 'value'), Input('f-sort', 'value')])
def am_table(n, fm, fd, fs):
    if not manager.backfill_complete:
        return []
    data = manager.get_am_data()
    if not data:
        return []
    rows = []
    for d in data:
        if fm == 'tradable' and not d.get('is_tradable'):
            continue
        if fd != 'ALL' and d.get('direction') != fd:
            continue
        sd = d.get('slope_details', {})
        w52 = d.get('week52_percentile')
        rows.append({
            '✓': '✅' if d.get('is_tradable') else '',
            'SYM': d['symbol'],
            'BAND': f"{d['threshold_pct']:.2f}%",
            'STS': d['stasis'],
            'DIR': d.get('direction') or '—',
            'SMS': d.get('sms', 0),
            'FMS': d.get('fms', 0),
            'TMS': d.get('tms', 0),
            'REV5': fmt_slope(sd.get('Rev_5')),
            'FCF5': fmt_slope(sd.get('FCF_5')),
            'FCFY': f"{sd['FCFY'] * 100:.1f}%" if sd.get('FCFY') else '—',
            '52W': f"{w52:.0f}%" if w52 is not None else '—',
            'PRICE': f"${d['current_price']:.2f}" if d.get('current_price') else '—',
            'TP': f"${d['take_profit']:.2f}" if d.get('take_profit') else '—',
            'SL': f"${d['stop_loss']:.2f}" if d.get('stop_loss') else '—',
            'R:R': fmt_rr(d.get('risk_reward')),
            'DUR': d.get('stasis_duration_str', '—'),
            '_tms': d.get('tms', 0),
            '_fms': d.get('fms', 0),
            '_stasis': d['stasis'],
            '_52w': w52 if w52 is not None else 999,
        })
    if not rows:
        return []
    df = pd.DataFrame(rows)
    sort_map = {'tms': '_tms', 'fms': '_fms', 'stasis': '_stasis', '52w': '_52w'}
    col = sort_map.get(fs, '_tms')
    df = df.sort_values(col, ascending=(fs == '52w')).head(200)
    df = df.drop(columns=['_tms', '_fms', '_stasis', '_52w'], errors='ignore')
    return df.to_dict('records')


# Symbol selection API - called by clientside callback and desktop app
app.clientside_callback(
    """function(rows, data) {
        if (!rows || !rows.length || !data) return '';
        var sym = data[rows[0]]['SYM'];
        if (sym) {
            fetch('/api/symbol/' + sym);
            // Notify parent window (desktop app) if embedded
            try {
                if (window.parent && window.parent !== window) {
                    window.parent.postMessage({type: 'symbolSelected', symbol: sym}, '*');
                }
            } catch(e) {}
        }
        return sym;
    }""",
    Output('status', 'title'),
    Input('tbl', 'selected_rows'), State('tbl', 'data'),
    prevent_initial_call=True)


@server.route('/api/symbol/<symbol>')
def set_symbol_api(symbol):
    set_selected_symbol(symbol)
    return json.dumps({'ok': True, 'symbol': symbol})


@server.route('/api/symbol')
def get_symbol_api():
    sym = get_selected_symbol()
    return json.dumps({'symbol': sym})


@server.route('/api/health')
def health_check():
    return json.dumps({
        'status': 'ok',
        'app': 'stasis_am',
        'initialized': manager.initialized,
        'backfill_complete': manager.backfill_complete,
        'backfill_progress': manager.backfill_progress,
        'stream_count': manager.stream_count,
        'tradable_count': manager.tradable_count,
        'price_feed': price_feed.get_status(),
        'fundamentals': len(config.fundamental_slopes),
    })


@server.route('/api/status')
def status_api():
    return json.dumps({
        'backfill_complete': manager.backfill_complete,
        'backfill_progress': manager.backfill_progress,
        'tradable_count': manager.tradable_count,
        'price_feed': price_feed.get_status(),
    })


# ============================================================================
# INITIALIZATION
# ============================================================================

_init_done = False


def initialize_data():
    global _init_done
    if _init_done:
        return
    print("=" * 70)
    print("  STASIS AM SERVER v2.1")
    print("  © 2026 Truth Communications LLC")
    print("=" * 70)
    print(f"\n🎯 {len(config.symbols)} symbols to process\n")

    config.week52_data = fetch_52_week_data()
    config.volumes = fetch_volume_data()
    fetch_all_fundamental_data()
    manager.backfill()
    price_feed.start()
    manager.start()

    print(f"\n✅ STASIS AM READY")
    print(f"   Fundamentals: {len(config.fundamental_slopes)}")
    print(f"   Streams: {manager.stream_count}")
    print(f"   Tradable: {manager.tradable_count}")
    _init_done = True


# Start initialization in background thread
init_thread = threading.Thread(target=initialize_data, daemon=True)
init_thread.start()

# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == '__main__':
    print(f"\n🚀 LAUNCHING STASIS AM SERVER on {HOST}:{PORT}\n")
    app.run(debug=False, host=HOST, port=PORT, use_reloader=False)
