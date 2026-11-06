import streamlit as st
import pandas as pd
import plotly.express as px

from modules.data_loader import (
    load_all_data,
    normalize_portfolio,
    normalize_capital,
    load_cashflow,
)

from modules.portfolio import (
    calculate_portfolio,
    calculate_crypto,
)

from modules.personal_finance import (
    calculate_financial_metrics,
)

from modules.risk_management import (
    show_risk_dashboard,
)

from modules.performance import (
    show_performance_dashboard,
)

from modules.macro_economy import (
    show_macro_dashboard,
)

from modules.loan_calculator import (
    calculate_loan,
)


# ==========================================
# 頁面設定
# ==========================================

st.set_page_config(
    page_title="Youi's Wealth Dashboard",
    page_icon="📈",
    layout="wide",
)

st.title("📈 Youi's Personal Wealth Dashboard")

st.caption(
    "Personal Wealth Management System | "
    "資產、槓桿、流動性、現金流及投資績效"
)


# ==========================================
# 資料載入
# ==========================================

with st.spinner("正在同步 Google Sheets 與市場資料..."):

    raw_data = load_all_data()

    data = raw_data.copy()

    data["portfolio"] = normalize_portfolio(
        raw_data["portfolio"]
    )

    data["capital"] = normalize_capital(
        raw_data["capital"]
    )

    data["cashflow"] = load_cashflow(
        raw_data["cashflow"]
    )

    portfolio = calculate_portfolio(
        data["portfolio"]
    )

    crypto = calculate_crypto(
        raw_data["crypto"]
    )

    metrics = calculate_financial_metrics(
        data,
        portfolio,
        crypto,
    )


# ==========================================
# 側邊欄
# ==========================================

with st.sidebar:

    st.title("⚙️ 系統控制")

    st.write("資料來源：Google Sheets")

    if st.button("🔄 重新整理資料", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.divider()

    st.write("**目前資產分類**")

    st.write("📈 台股 / 美股")

    st.write("₿ 加密貨幣")

    st.write("🏦 銀行現金及負債")

    st.write("🏠 房地產及房貸")

    st.divider()

    st.caption(
        "本系統提供財務資訊及風險分析，"
        "不構成投資建議。"
    )


# ==========================================
# 第一區：資產總覽
# ==========================================

st.header("💰 一、個人資產總覽")

c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "總資產",
    f'NT$ {metrics["total_assets"]:,.0f}'
)

c2.metric(
    "總負債",
    f'NT$ {metrics["total_liabilities"]:,.0f}'
)

c3.metric(
    "淨資產",
    f'NT$ {metrics["net_worth"]:,.0f}'
)

c4.metric(
    "投資資產",
    f'NT$ {metrics["investment_assets"]:,.0f}'
)

st.divider()


# ==========================================
# 第二區：資產配置
# ==========================================

st.header("📊 二、資產配置")

asset_data = pd.DataFrame({
    "資產類型": [
        "現金",
        "股票",
        "加密貨幣",
        "房地產",
    ],
    "金額": [
        metrics["cash_assets"],
        metrics["stock_assets"],
        metrics["crypto_assets"],
        metrics["property_value"],
    ]
})

asset_data = asset_data[
    asset_data["金額"] > 0
]

if not asset_data.empty:

    col1, col2 = st.columns(2)

    with col1:

        fig = px.pie(
            asset_data,
            names="資產類型",
            values="金額",
            hole=0.5,
            title="資產配置比例",
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    with col2:

        st.dataframe(
            asset_data,
            use_container_width=True,
            hide_index=True
        )

else:
    st.info("尚無可顯示的資產資料。")


# ==========================================
# 第三區：投資部位
# ==========================================

st.header("📈 三、投資部位")

tab1, tab2 = st.tabs([
    "股票投資",
    "加密貨幣",
])

with tab1:

    if not portfolio.empty:

        st.metric(
            "股票總市值",
            f'NT$ {metrics["stock_assets"]:,.0f}'
        )

        st.dataframe(
            portfolio,
            use_container_width=True,
            hide_index=True
        )

    else:
        st.info("尚無股票資料。")


with tab2:

    if not crypto.empty:

        st.metric(
            "加密貨幣總市值",
            f'NT$ {metrics["crypto_assets"]:,.0f}'
        )

        st.dataframe(
            crypto,
            use_container_width=True,
            hide_index=True
        )

    else:
        st.info("尚無加密貨幣資料。")


st.divider()


# ==========================================
# 第四區：CLEC 風險管理
# ==========================================

show_risk_dashboard(metrics)

st.divider()


# ==========================================
# 第五區：流動性
# ==========================================

st.header("💧 五、流動性管理")

c1, c2, c3 = st.columns(3)

c1.metric(
    "可動用現金",
    f'NT$ {metrics["cash_assets"]:,.0f}'
)

c2.metric(
    "理財型房貸可用額度",
    f'NT$ {metrics["available_credit"]:,.0f}'
)

c3.metric(
    "應急準備金",
    f'{metrics["emergency_months"]:.1f} 個月'
)

c1, c2, c3 = st.columns(3)

c1.metric(
    "現金流動性",
    f'{metrics["cash_liquidity"]:.2f}x'
)

c2.metric(
    "備用額度流動性",
    f'{metrics["reserve_liquidity"]:.2f}x'
)

c3.metric(
    "總流動性",
    f'{metrics["total_liquidity"]:.2f}x'
)

st.caption(
    "流動性指標以目前資料估算，"
    "不代表所有資產都能立即變現。"
)

st.divider()


# ==========================================
# 第六區：每月現金流
# ==========================================

st.header("💵 六、每月現金流")

c1, c2, c3 = st.columns(3)

c1.metric(
    "每月收入",
    f'NT$ {metrics["income"]:,.0f}'
)

c2.metric(
    "每月支出",
    f'NT$ {metrics["expenses"]:,.0f}'
)

c3.metric(
    "每月淨現金流",
    f'NT$ {metrics["net_cashflow"]:,.0f}'
)

c1, c2, c3 = st.columns(3)

c1.metric(
    "儲蓄率",
    f'{metrics["savings_rate"] * 100:.1f}%'
)

c2.metric(
    "還款負擔率",
    f'{metrics["debt_service_ratio"] * 100:.1f}%'
)

c3.metric(
    "財務自由度",
    f'{metrics["financial_independence"] * 100:.1f}%'
)

if metrics["net_cashflow"] < 0:
    st.error("每月現金流為負，請檢查收入及固定支出。")

if metrics["debt_service_ratio"] > 0.3:
    st.warning("還款負擔率超過 30%，建議留意現金流壓力。")

st.divider()


# ==========================================
# 第七區：貸款試算
# ==========================================

st.header("🏦 七、貸款試算")

with st.expander("開啟貸款試算工具"):

    loan_col1, loan_col2, loan_col3 = st.columns(3)

    with loan_col1:
        principal = st.number_input(
            "貸款本金（元）",
            min_value=0,
            value=1300000,
            step=10000,
        )

    with loan_col2:
        rate = st.number_input(
            "年利率（%）",
            min_value=0.0,
            value=2.81,
            step=0.01,
        )

    with loan_col3:
        months = st.number_input(
            "貸款期數（月）",
            min_value=1,
            value=84,
            step=1,
        )

    result = calculate_loan(
        principal,
        rate / 100,
        months,
    )

    st.metric(
        "每月還款金額",
        f'NT$ {result["monthly_payment"]:,.0f}'
    )

    st.metric(
        "總利息",
        f'NT$ {result["total_interest"]:,.0f}'
    )

    st.metric(
        "總還款金額",
        f'NT$ {result["total_payment"]:,.0f}'
    )


st.divider()


# ==========================================
# 第八區：投資績效
# ==========================================

show_performance_dashboard(
    data,
    portfolio,
    metrics,
)

st.divider()


# ==========================================
# 第九區：總體經濟
# ==========================================

show_macro_dashboard()


# ==========================================
# 第十區：原始資料檢查
# ==========================================

st.divider()

with st.expander("🔍 查看 Google Sheets 原始資料"):

    for name, df in raw_data.items():

        st.subheader(name)

        if isinstance(df, pd.DataFrame) and not df.empty:
            st.dataframe(
                df,
                use_container_width=True
            )
        else:
            st.info("目前沒有資料。")


st.caption(
    "Youi's Personal Wealth Dashboard | "
    "Financial data is for reference only."
)