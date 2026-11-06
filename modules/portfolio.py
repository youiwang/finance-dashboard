import yfinance as yf
import pandas as pd
import streamlit as st
import re

from modules.data_loader import clean_number
from modules.config import LEVERAGE_OVERRIDES


@st.cache_data(ttl=900, show_spinner=False)
def get_fx_rate(currency):
    currency = str(currency).upper()

    if currency == "TWD":
        return 1.0

    try:
        ticker = f"{currency}TWD=X"
        data = yf.Ticker(ticker).history(period="5d")

        if not data.empty:
            return float(data["Close"].dropna().iloc[-1])

    except Exception:
        pass

    return None


@st.cache_data(ttl=900, show_spinner=False)
def get_stock_price(symbol):
    candidates = _build_symbol_candidates(symbol)

    for ticker in candidates:
        try:
            data = yf.Ticker(ticker).history(period="5d")

            if not data.empty:
                return float(data["Close"].dropna().iloc[-1]), ticker

        except Exception:
            continue

    return None, ""


def _normalize_ticker_code(symbol):
    text = str(symbol).strip().upper()

    if text.lower() == "nan" or text == "":
        return ""

    if text.endswith(".0"):
        try:
            text = str(int(float(text)))
        except ValueError:
            return text

    if text.isdigit():
        return text.zfill(4)

    matched = re.match(r"^(\d+)([A-Z]+)$", text)
    if matched:
        num, suffix = matched.groups()
        return f"{num.zfill(5)}{suffix}"

    return text


def _build_symbol_candidates(symbol):
    normalized = _normalize_ticker_code(symbol)

    if not normalized:
        return []

    candidates = [normalized]

    if normalized.isdigit():
        candidates = [
            f"{normalized}.TW",
            f"{normalized}.TWO",
            normalized,
        ]
    elif re.match(r"^\d+[A-Z]+$", normalized):
        numeric_part = re.match(r"^(\d+)", normalized).group(1)
        candidates = [
            f"{normalized}.TW",
            f"{normalized}.TWO",
            normalized,
            f"{numeric_part}.TW",
            f"{numeric_part}.TWO",
        ]

    dedup = []
    for item in candidates:
        if item not in dedup:
            dedup.append(item)
    return dedup


def is_leveraged(row):
    symbol = str(row.get("代號", "")).upper()
    name = str(row.get("標的名稱", ""))

    if symbol in LEVERAGE_OVERRIDES:
        return float(LEVERAGE_OVERRIDES[symbol])

    if "正2" in name or symbol.endswith("L"):
        return 2.0

    return 1.0


def calculate_portfolio(df):
    df = df.copy()

    if df.empty:
        return df

    df["代號"] = df["代號"].apply(_normalize_ticker_code)

    invalid_symbols = {"", "0", "0000", "NAN", "NONE"}
    df = df[~df["代號"].isin(invalid_symbols)].copy()

    if df.empty:
        return df

    for col in [
        "持有股數", "平均成本", "總成本",
        "即時股價", "即時市值"
    ]:
        df[col] = df[col].apply(clean_number)

    prices = []
    values = []
    costs = []
    fx_rates = []
    exposures = []
    quote_sources = []
    quote_tickers = []
    quote_candidates = []
    value_sources = []

    for _, row in df.iterrows():
        symbol = _normalize_ticker_code(row["代號"])
        currency = str(row.get("幣別", "TWD")).upper()
        candidates = _build_symbol_candidates(symbol)

        fx = get_fx_rate(currency)

        if fx is None:
            fx = 1.0 if currency == "TWD" else None

        live_price, quote_ticker = get_stock_price(symbol)
        sheet_price = clean_number(row["即時股價"])

        if live_price is not None and live_price > 0:
            price = live_price
            quote_source = "yfinance"
        elif sheet_price > 0:
            price = sheet_price
            quote_source = "sheet_price"
        else:
            price = 0.0
            quote_source = "unavailable"

        # 報價失敗時，使用 Google Sheets 已有市值
        if price > 0:
            market_value = (
                price * row["持有股數"] * (fx or 1.0)
            )
            value_source = "price_x_qty"
        else:
            manual_market_value = (
                clean_number(row["即時市值"]) * (fx or 1.0)
            )
            market_value = manual_market_value if manual_market_value > 0 else 0
            value_source = "sheet_market_value" if manual_market_value > 0 else "unavailable"

        cost = (
            row["總成本"] if row["總成本"] > 0
            else row["平均成本"] * row["持有股數"]
        )

        # 成本也必須換算成台幣
        cost_twd = cost * (fx or 1.0)

        if market_value <= 0 and cost_twd > 0:
            market_value = cost_twd
            value_source = "cost_fallback"

        prices.append(price if price is not None else 0.0)
        values.append(market_value)
        costs.append(cost_twd)
        fx_rates.append(fx or 0)
        exposures.append(
            market_value * is_leveraged(row)
        )
        quote_sources.append(quote_source)
        quote_tickers.append(quote_ticker)
        quote_candidates.append(" | ".join(candidates))
        value_sources.append(value_source)

    df["最新價格"] = prices
    df["匯率"] = fx_rates
    df["台幣市值"] = values
    df["台幣成本"] = costs
    df["台幣損益"] = df["台幣市值"] - df["台幣成本"]
    df["實質曝險"] = exposures
    df["報價來源"] = quote_sources
    df["報價代號"] = quote_tickers
    df["候選代號"] = quote_candidates
    df["市值來源"] = value_sources

    df["報酬率"] = (
        df["台幣損益"] / df["台幣成本"] * 100
    ).where(df["台幣成本"] > 0, 0)

    df = df[
        (df["持有股數"] > 0)
        | (df["台幣成本"] > 0)
        | (df["台幣市值"] > 0)
    ].copy()

    return df


@st.cache_data(ttl=900, show_spinner=False)
def calculate_crypto_price(symbol):
    try:
        ticker_map = {
            "BTC": "BTC-USD",
            "ETH": "ETH-USD",
            "SOL": "SOL-USD",
            "BNB": "BNB-USD",
            "XRP": "XRP-USD",
        }

        ticker = ticker_map.get(
            str(symbol).upper(),
            f"{symbol}-USD"
        )

        data = yf.Ticker(ticker).history(period="5d")

        if not data.empty:
            return float(data["Close"].dropna().iloc[-1])

    except Exception:
        pass

    return 0.0


def calculate_crypto(df):
    if df.empty:
        return pd.DataFrame()

    df = df.copy()

    results = []

    for _, row in df.iterrows():
        symbol = str(row.get("幣種", "")).upper()
        quantity = clean_number(row.get("持有數量", 0))
        currency = str(row.get("幣別", "USD")).upper()
        cost_price = clean_number(row.get("成本單價", 0))

        price = calculate_crypto_price(symbol)

        if price <= 0:
            price = cost_price

        fx = get_fx_rate(currency)

        if fx is None:
            fx = 0

        value = quantity * price * fx
        cost = quantity * cost_price * fx

        results.append({
            "幣種": symbol,
            "持有數量": quantity,
            "最新價格": price,
            "台幣市值": value,
            "台幣成本": cost,
            "台幣損益": value - cost,
        })

    return pd.DataFrame(results)