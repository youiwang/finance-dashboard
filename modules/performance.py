import numpy as np
import pandas as pd
import streamlit as st

from modules.data_loader import clean_number


def calculate_cagr(begin_value, end_value, years):
    if begin_value <= 0 or end_value <= 0 or years <= 0:
        return 0

    return (end_value / begin_value) ** (1 / years) - 1


def calculate_xirr(cashflows, dates):
    """
    dates: datetime 日期列表
    cashflows: 現金流列表
    投入為負數，提領及期末價值為正數。
    """
    if len(cashflows) < 2:
        return None

    dates = pd.to_datetime(dates)

    days = (
        dates - dates.min()
    ).days / 365.0

    if not (any(x < 0 for x in cashflows)
            and any(x > 0 for x in cashflows)):
        return None

    def npv(rate):
        if rate <= -1:
            return float("inf")

        return sum(
            cf / (1 + rate) ** day
            for cf, day in zip(cashflows, days)
        )

    low = -0.9999
    high = 1.0

    try:
        if npv(low) * npv(high) > 0:
            for _ in range(20):
                high = high * 2 + 1
                if npv(low) * npv(high) <= 0:
                    break
            else:
                return None

        for _ in range(200):
            mid = (low + high) / 2
            value = npv(mid)

            if abs(value) < 0.01:
                return mid

            if npv(low) * value <= 0:
                high = mid
            else:
                low = mid

        return (low + high) / 2

    except (OverflowError, ValueError, ZeroDivisionError):
        return None


def show_performance_dashboard(data, portfolio, metrics):
    st.header("📈 投資績效")

    st.metric(
        "投資資產",
        f'NT$ {metrics["investment_assets"]:,.0f}'
    )

    st.metric(
        "投資成本",
        f'NT$ {metrics["investment_cost"]:,.0f}'
    )

    profit = (
        metrics["investment_assets"]
        - metrics["investment_cost"]
    )

    st.metric(
        "投資帳面損益",
        f'NT$ {profit:,.0f}',
        delta=f'{profit:,.0f} TWD'
    )

    if not portfolio.empty:
        st.subheader("股票投資部位")

        display_cols = [
            "代號",
            "標的名稱",
            "持有股數",
            "最新價格",
            "台幣市值",
            "台幣成本",
            "台幣損益",
            "報酬率",
        ]

        st.dataframe(
            portfolio[display_cols],
            use_container_width=True,
            hide_index=True
        )

    history = data.get("performance", pd.DataFrame())

    if history.empty:
        st.info(
            "尚未建立投資歷史紀錄。"
            "請在 Performance 工作表新增交易資料。"
        )
        return

    st.subheader("歷史投資現金流")

    history = history.copy()

    required = ["日期", "交易類型", "金額"]

    if not all(col in history.columns for col in required):
        st.warning("Performance 欄位尚未符合規格。")
        return

    history["日期"] = pd.to_datetime(
        history["日期"], errors="coerce"
    )

    history["金額"] = history["金額"].apply(clean_number)

    history = history.dropna(subset=["日期"])

    st.dataframe(history, use_container_width=True)

    # 此處先顯示歷史交易，完整 XIRR
    # 需要在期末增加一筆最新總市值。