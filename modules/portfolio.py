import yfinance as yf
import pandas as pd
import streamlit as st

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
    try:
        data = yf.Ticker(str(symbol)).history(period="5d")

        if not data.empty:
            return float(data["Close"].dropna().iloc[-1])

    except Exception:
        pass

    return None


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

    for _, row in df.iterrows():
        symbol = str(row["代號"])
        currency = str(row.get("幣別", "TWD")).upper()

        fx = get_fx_rate(currency)

        if fx is None:
            fx = 1.0 if currency == "TWD" else None

        price = get_stock_price(symbol)

        if price is None:
            price = clean_number(row["即時股價"])

        # 報價失敗時，使用 Google Sheets 已有市值
        if price > 0:
            market_value = (
                price * row["持有股數"] * (fx or 1.0)
            )
        else:
            market_value = (
                clean_number(row["即時市值"]) * (fx or 1.0)
            )

        cost = (
            row["總成本"] if row["總成本"] > 0
            else row["平均成本"] * row["持有股數"]
        )

        # 成本也必須換算成台幣
        cost_twd = cost * (fx or 1.0)

        prices.append(price)
        values.append(market_value)
        costs.append(cost_twd)
        fx_rates.append(fx or 0)
        exposures.append(
            market_value * is_leveraged(row)
        )

    df["最新價格"] = prices
    df["匯率"] = fx_rates
    df["台幣市值"] = values
    df["台幣成本"] = costs
    df["台幣損益"] = df["台幣市值"] - df["台幣成本"]
    df["實質曝險"] = exposures

    df["報酬率"] = (
        df["台幣損益"] / df["台幣成本"] * 100
    ).where(df["台幣成本"] > 0, 0)

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