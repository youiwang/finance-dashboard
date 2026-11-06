import streamlit as st
import yfinance as yf
import requests


@st.cache_data(ttl=3600)
def get_market_data(symbol, period="1y"):
    try:
        data = yf.Ticker(symbol).history(period=period)

        if data.empty:
            return None

        return data

    except Exception:
        return None


@st.cache_data(ttl=86400)
def get_ndc_light():
    try:
        url = (
            "https://openapi.ndc.gov.tw/api/odata/"
            "od/Indicators?$top=1&$orderby=date%20desc"
        )

        response = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10
        )

        response.raise_for_status()

        data = response.json()

        score = float(data["value"][0]["Value"])

        if score >= 38:
            light = "🔴 紅燈"

        elif score >= 32:
            light = "🟠 黃紅燈"

        elif score >= 23:
            light = "🟢 綠燈"

        elif score >= 17:
            light = "🟡 黃藍燈"

        else:
            light = "🔵 藍燈"

        return score, light

    except Exception:
        return 0, "暫無資料"


def show_macro_dashboard():
    st.header("🌍 總體經濟與市場狀態")

    vix = get_market_data("^VIX", "5d")
    sp500 = get_market_data("^GSPC", "1y")

    vix_value = (
        float(vix["Close"].dropna().iloc[-1])
        if vix is not None else 0
    )

    if sp500 is not None:
        current = float(sp500["Close"].dropna().iloc[-1])
        high = float(sp500["High"].max())

        drawdown = (
            (current - high) / high * 100
            if high > 0 else 0
        )
    else:
        drawdown = 0

    score, light = get_ndc_light()

    c1, c2, c3 = st.columns(3)

    c1.metric("VIX 恐慌指數", f"{vix_value:.2f}")

    c2.metric("S&P 500 回檔", f"{drawdown:.2f}%")

    c3.metric("台灣景氣燈號", f"{score:.0f} 分", light)

    st.subheader("CLEC 動態曝險參考")

    if vix_value > 40:
        st.error("極度恐慌：檢查現金與流動性，避免無計畫動用全部現金。")

    elif drawdown <= -30:
        st.error("市場深度回檔：重新檢查整體槓桿與可承受損失。")

    elif drawdown <= -20:
        st.warning("市場明顯回檔：檢查資產配置及現金緩衝。")

    elif drawdown <= -10:
        st.info("市場進入回檔：檢視投資組合風險。")

    elif vix_value < 15 and vix_value > 0:
        st.warning("市場波動偏低：留意過度承擔槓桿風險。")

    else:
        st.success("市場狀態相對平穩。")

    st.caption(
        "市場指標僅供風險觀察，不構成買賣訊號。"
        "請勿單憑 VIX 或回檔幅度自動加槓桿。"
    )