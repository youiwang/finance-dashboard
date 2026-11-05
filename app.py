import streamlit as st
import yfinance as yf
import pandas_datareader.data as web
import datetime
from streamlit_gsheets import GSheetsConnection

st.title("個人投資儀表板")

# 建立與 Google Sheets 的連線
conn = st.connection("gsheets", type=GSheetsConnection)

# 讀取資料 (會自動轉為 Pandas DataFrame)
# 可以直接貼上整串 Google Sheet URL，或是使用 Spreadsheet ID
spreadsheet_url = "https://docs.google.com/spreadsheets/d/1WvqwEcs-k92EXw90P_6hY5bqgZgA3jyMDFNSQZbP3AA/edit?gid=0#gid=0"
df_portfolio = conn.read(spreadsheet=spreadsheet_url, worksheet="Portfolio")
df_capital = conn.read(spreadsheet=spreadsheet_url, worksheet="Capital")

st.write("目前持股與現金部位狀態：")
st.dataframe(df_portfolio)

st.header("市場景氣與動態策略指標")

# 1. 抓取 VIX 恐慌指數
vix_data = yf.Ticker("^VIX").history(period="1d")
vix_current = vix_data['Close'].iloc[-1]

# 2. 抓取 S&P 500 計算回檔幅度 (Drawdown)
sp500_data = yf.Ticker("^GSPC").history(period="1y")
sp500_high = sp500_data['High'].max()
sp500_current = sp500_data['Close'].iloc[-1]
drawdown = (sp500_current - sp500_high) / sp500_high * 100

# 3. 抓取 FRED 總經數據 (例如 M2 貨幣供給，用來算市值/資金比)
end_date = datetime.date.today()
start_date = end_date - datetime.timedelta(days=365)
m2_supply = web.DataReader("WM2NS", "fred", start_date, end_date) # 每週 M2 供給

# --- 儀表板顯示市場狀態 ---
col1, col2, col3 = st.columns(3)
col1.metric("VIX 恐慌指數", f"{vix_current:.2f}")
col2.metric("S&P 500 距高點回檔", f"{drawdown:.2f}%")

# 根據 Podcast 邏輯提供動態曝險建議
st.subheader("動態曝險策略建議 (CLEC 4:4:2 基準)")
if vix_current > 40:
    st.error("極度恐慌 (VIX > 40)：絕佳加碼時機，全面動用現金！")
elif drawdown <= -40:
    st.error("深度崩盤 (回檔 > 40%)：賣出 0050，全數轉入 0050正2 放大底部曝險。")
elif drawdown <= -30:
    st.warning("嚴重回檔 (回檔 30%)：打入剩餘 40%-50% 現金。")
elif drawdown <= -20:
    st.warning("中度回檔 (回檔 20%)：打入 30% 現金。")
elif drawdown <= -10:
    st.info("首波回檔 (回檔 10%)：打入 20% 現金。")
elif vix_current < 15:
    st.success("市場狂熱 (VIX < 15)：將 0050正2 獲利了結轉回 0050/現金，恢復 4:4:2。")
else:
    st.write("市場平穩，維持 40% 0050、40% 0050正2、20% 現金。")

st.header("個人財務與風險控管")

# 計算各項總和
# 股票投資部位 (從 Portfolio 計算即時市值總和)
if '即時市值' in df_portfolio.columns:
    stock_assets = df_portfolio['即時市值'].sum()
else:
    stock_assets = 0

# 現金與其他活存 (從 Capital 撈出金額大於0的項目)
if '金額' in df_capital.columns:
    cash_assets = df_capital[df_capital['金額'] > 0]['金額'].sum()
    # 總負債 (從 Capital 撈出金額小於0的項目，轉為絕對值)
    total_liabilities = abs(df_capital[df_capital['金額'] < 0]['金額'].sum())
else:
    cash_assets = 0
    total_liabilities = 0

# 1. 淨資產與總資產
total_assets = stock_assets + cash_assets
net_worth = total_assets - total_liabilities

# 2. 資產負債比 = (總負債 / 總資產) * 100%
leverage_ratio = (total_liabilities / total_assets) * 100 if total_assets > 0 else 0

# 3. 證金維持率 = (質押市值 / 借款金額) * 100%
if '項目類別' in df_capital.columns and '金額' in df_capital.columns and '質押市值' in df_capital.columns:
    pledge_data = df_capital[df_capital['項目類別'] == '股票質押']
    pledge_loans = abs(pledge_data['金額'].sum())
    pledge_value = pledge_data['質押市值'].sum()
    maintenance_margin = (pledge_value / pledge_loans) * 100 if pledge_loans > 0 else 0
else:
    maintenance_margin = 0

# --- 儀表板顯示個人財報 ---
col_a, col_b, col_c = st.columns(3)
col_a.metric("淨資產 (Net Worth)", f"${net_worth:,.0f}")
col_b.metric("資產負債比", f"{leverage_ratio:.1f}%", 
             delta="負債偏高" if leverage_ratio > 50 else "健康", 
             delta_color="inverse")

# 維持率特別設定顏色警告
if maintenance_margin > 0:
    margin_status = "斷頭風險！" if maintenance_margin < 166 else "安全"
    col_c.metric("股票質押維持率", f"{maintenance_margin:.1f}%", 
                 delta=margin_status, 
                 delta_color="inverse")

st.divider()

# 4. 流動性與現金流指標 (可根據實際填入的月收支欄位計算)
# 假設 Capital 表有定義 '每月總收入' 與 '每月總還款' 的欄位
monthly_income = 80000 # 範例數字，請替換為試算表抓取的變數
monthly_debt_pay = 15000 
debt_service_ratio = (monthly_debt_pay / monthly_income) * 100

st.write(f"**還款負擔率 (Debt Service Ratio):** {debt_service_ratio:.1f}% (建議低於 30%)")
st.write(f"**應急準備金存量:** {cash_assets / 40000:.1f} 個月 (假設每月必需支出為 4萬)")