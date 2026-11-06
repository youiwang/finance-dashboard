import streamlit as st
from streamlit_gsheets import GSheetsConnection
import yfinance as yf
import pandas as pd
import requests
import datetime

# --- 頁面基本設定 ---
st.set_page_config(page_title="個人投資儀表板", page_icon="📈", layout="wide")
st.title("📈 個人投資與財務儀表板")

# --- 輔助函數：抓取國發會景氣燈號 ---
@st.cache_data(ttl=86400) # 快取一天，避免重複打 API
def get_ndc_light():
    try:
        # 國發會開放資料 API (綜合判斷分數)
        url = "https://openapi.ndc.gov.tw/api/odata/od/Indicators?$top=1&$orderby=date%20desc"
        res = requests.get(url).json()
        score = int(res['value'][0]['Value'])
        
        # 判斷燈號顏色
        if score >= 38: return score, "🔴 紅燈 (過熱，分批獲利了結)"
        elif score >= 32: return score, "🟡 黃紅燈 (注意風險)"
        elif score >= 23: return score, "🟢 綠燈 (穩定)"
        elif score >= 17: return score, "🟡 黃藍燈 (注意建倉機會)"
        else: return score, "🔵 藍燈 (低迷，絕佳建倉期)"
    except:
        return 0, "暫無資料"

# ==========================================
# 區塊一：總體經濟與市場狀態
# ==========================================
st.header("🌍 市場景氣與動態策略指標")

# 1. 抓取市場數據
try:
    # 抓取 VIX 恐慌指數
    vix_data = yf.Ticker("^VIX").history(period="1d")
    vix_current = vix_data['Close'].iloc[-1] if not vix_data.empty else 0

    # 抓取 S&P 500 計算回檔幅度 (Drawdown)
    sp500_data = yf.Ticker("^GSPC").history(period="1y")
    sp500_high = sp500_data['High'].max()
    sp500_current = sp500_data['Close'].iloc[-1] if not sp500_data.empty else 1
    drawdown = (sp500_current - sp500_high) / sp500_high * 100
except:
    vix_current, drawdown = 0, 0
    st.error("無法取得 Yahoo Finance 市場資料，請稍後再試。")

ndc_score, ndc_light = get_ndc_light()

# 2. 顯示市場指標
col1, col2, col3 = st.columns(3)
col1.metric("VIX 恐慌指數", f"{vix_current:.2f}")
col2.metric("S&P 500 距高點回檔", f"{drawdown:.2f}%")
col3.metric("台灣景氣對策信號", f"{ndc_score} 分", delta=ndc_light, delta_color="normal")

# 3. 動態曝險策略建議
st.subheader("💡 動態曝險策略建議 (CLEC 4:4:2 基準)")
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
    st.success("市場狂熱 (VIX < 15)：將 0050正2 獲利了結轉回 0050/現金，恢復 4:4:2 基準。")
else:
    st.write("市場平穩，建議維持 40% 0050、40% 0050正2、20% 現金配置。")

st.divider()

# ==========================================
# 區塊二：個人財務與風險控管
# ==========================================
st.header("💼 個人財務與風險控管")

# 1. 建立連線並讀取 Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)
SHEET_URL = "https://docs.google.com/spreadsheets/d/1WvqwEcs-k92EXw90P_6hY5bqgZgA3jyMDFNSQZbP3AA/edit?gid=0#gid=0"

try:
    df_portfolio = conn.read(spreadsheet=SHEET_URL, worksheet="Portfolio")
    df_capital = conn.read(spreadsheet=SHEET_URL, worksheet="Capital")
except Exception as e:
    st.error(f"讀取 Google Sheets 失敗，請確認網址與工作表名稱是否正確。錯誤訊息: {e}")
    st.stop()

# 2. 資料清理：強制剔除 NT$、逗號等非數字字元，並轉為浮點數
df_capital['金額'] = pd.to_numeric(df_capital['金額'].astype(str).str.replace(r'[^\d.-]', '', regex=True), errors='coerce').fillna(0)
df_portfolio['即時市值'] = pd.to_numeric(df_portfolio['即時市值'].astype(str).str.replace(r'[^\d.-]', '', regex=True), errors='coerce').fillna(0)
df_capital['質押市值'] = pd.to_numeric(df_capital['質押市值'].astype(str).str.replace(r'[^\d.-]', '', regex=True), errors='coerce').fillna(0)

# 3. 計算基礎資產與負債
stock_assets = df_portfolio['即時市值'].sum()
cash_assets = df_capital[df_capital['金額'] > 0]['金額'].sum()
total_liabilities = abs(df_capital[df_capital['金額'] < 0]['金額'].sum())

total_assets = stock_assets + cash_assets
net_worth = total_assets - total_liabilities

# 4. 計算動態曝險金額 (若標的名稱含"正2"或代號含"L"，市值以 2 倍計算)
def calculate_exposure(row):
    if '正2' in str(row.get('標的名稱', '')) or 'L' in str(row.get('代號', '')):
        return row['即時市值'] * 2
    return row['即時市值']

total_exposure_value = df_portfolio.apply(calculate_exposure, axis=1).sum() + cash_assets
exposure_ratio = (total_exposure_value / net_worth) * 100 if net_worth > 0 else 0

# 5. 計算各項風險比例
leverage_ratio = (total_liabilities / total_assets) * 100 if total_assets > 0 else 0

pledge_data = df_capital[df_capital['項目類別'] == '股票質押']
pledge_loans = abs(pledge_data['金額'].sum())
pledge_value = pledge_data['質押市值'].sum()
maintenance_margin = (pledge_value / pledge_loans) * 100 if pledge_loans > 0 else 0

# 6. 渲染個人財務核心數據
col_a, col_b, col_c = st.columns(3)
col_a.metric("淨資產 (Net Worth)", f"${net_worth:,.0f}")
col_b.metric("資產負債比", f"{leverage_ratio:.1f}%", 
             delta="負債偏高" if leverage_ratio > 50 else "健康", 
             delta_color="inverse")
col_c.metric("實質曝險倍率", f"{exposure_ratio/100:.2f}x", 
             delta="滿倉/槓桿狀態" if exposure_ratio > 100 else "未滿倉",
             delta_color="off")

# 7. 警示維持率 (如果有使用股票質押才顯示)
if maintenance_margin > 0:
    if maintenance_margin < 166:
        st.error(f"🚨 **斷頭風險警告！** 股票質押維持率跌至 {maintenance_margin:.1f}%，請立即補足保證金！")
    elif maintenance_margin < 200:
        st.warning(f"⚠️ **股票質押維持率注意**: {maintenance_margin:.1f}% (建議維持在 200% 以上)")
    else:
        st.success(f"🛡️ **股票質押維持率**: {maintenance_margin:.1f}% (安全)")

st.divider()

# 8. 現金流與流動性 (這裡的收入與還款目前寫死為範例數值，未來你可以在 Sheet 中新增欄位來抓取)
monthly_income = 80000        # 每月總收入 (範例)
monthly_debt_pay = 15000      # 每月需還款本息 (範例)
monthly_living_exp = 40000    # 每月必需開銷 (範例)

debt_service_ratio = (monthly_debt_pay / monthly_income) * 100
emergency_fund_months = cash_assets / monthly_living_exp if monthly_living_exp > 0 else 0

col_d, col_e = st.columns(2)
with col_d:
    st.write(f"**還款負擔率 (Debt Service Ratio):** {debt_service_ratio:.1f}%")
    st.caption("衡量每月現金流被貸款吃掉的比例，建議控制在 30% 以下。")
with col_e:
    st.write(f"**應急準備金存量:** {emergency_fund_months:.1f} 個月")
    st.caption(f"目前活存現金為 ${cash_assets:,.0f}，假設每月必需支出為 4 萬。建議維持 6 個月以上。")

st.divider()

# 9. 顯示原始資料表 (可選，方便你在網頁上直接核對數字)
with st.expander("🔍 查看詳細資產與資金部位"):
    st.write("### 投資部位 (Portfolio)")
    st.dataframe(df_portfolio, use_container_width=True)
    st.write("### 資金與槓桿 (Capital)")
    st.dataframe(df_capital, use_container_width=True)