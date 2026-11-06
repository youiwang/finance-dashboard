import streamlit as st
import pandas as pd

from streamlit_gsheets import GSheetsConnection

@st.cache_resource
def get_connection():
    return st.connection(
        "gsheets",
        type=GSheetsConnection
    )

SHEET_URL = (
    "https://docs.google.com/spreadsheets/d/1WvqwEcs-k92EXw90P_6hY5bqgZgA3jyMDFNSQZbP3AA/edit?gid=0#gid=0"
)

SHEETS = {
    "portfolio": "Portfolio",
    "capital": "Capital",
    "crypto": "Crypto",
    "property": "Property",
    "cashflow": "Monthly Cashflow",
    "loan": "Personal loan",
    "performance": "Performance",
}

# DEFAULT_CASHFLOW = {
#     "每月薪資收入": 80000,
#     "其他收入": 0,
#     "每月被動收入": 0,
#     "每月生活費": 40000,
#     "每月貸款還款": 15000,
#     "每月信用卡支出": 0,
#     "其他固定支出": 0,
# }

def read_sheet(name, required=False):
    try:
        conn = get_connection()

        df = conn.read(
            spreadsheet=SHEET_URL,
            worksheet=SHEETS[name],
            ttl=0
        )

        if df is None:
            return pd.DataFrame()

        return df.dropna(how="all").reset_index(drop=True)

    except Exception as e:
        if required:
            st.error(f"讀取 {name} 工作表失敗：{e}")
            st.stop()

        st.warning(
            f"工作表 {SHEETS[name]} 尚未建立或無法讀取。"
        )
        return pd.DataFrame()


def clean_number(value):
    if pd.isna(value):
        return 0.0

    text = str(value).strip()

    if not text:
        return 0.0

    text = (
        text.replace(",", "")
        .replace("NT$", "")
        .replace("$", "")
        .replace("USD", "")
        .replace("TWD", "")
        .replace("%", "")
        .strip()
    )

    try:
        return float(text)
    except (ValueError, TypeError):
        return 0.0


def load_all_data():
    data = {}

    for key in SHEETS:
        data[key] = read_sheet(
            key,
            required=(key in ["portfolio", "capital"])
        )

    return data


def normalize_table(df):
    """
    將第一欄為欄位名稱的直向資料表，
    轉成標準欄位名稱。
    """
    if df.empty:
        return pd.DataFrame()

    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    return df


def normalize_portfolio(df):
    """
    Portfolio 橫向格式：
    A欄為資料項目
    B欄以後為各個投資標的
    """

    if df.empty:
        return pd.DataFrame()

    df = df.copy()

    df.columns = [
        str(c).strip()
        for c in df.columns
    ]

    # 第一欄是資料項目
    first_col = df.columns[0]

    df[first_col] = (
        df[first_col]
        .astype(str)
        .str.strip()
    )

    # 將資料項目轉成欄位名稱
    df = df.set_index(first_col).T

    df.index.name = "原始欄位"

    df = df.reset_index(drop=True)

    # 欄位名稱統一
    df.columns = [
        str(c).strip()
        for c in df.columns
    ]

    aliases = {
        "代號": ["代號", "股票代號", "代碼"],
        "標的名稱": ["標的名稱", "名稱"],
        "持有股數": ["持有股數", "持有數量", "股數"],
        "平均成本": ["平均成本", "成本"],
        "總成本": ["總成本"],
        "即時股價": ["即時股價", "目前股價", "股價"],
        "即時市值": ["即時市值", "市值"],
        "未實現損益": ["未實現損益", "損益"],
        "幣別": ["幣別", "Currency"],
        "資產類型": ["資產類型", "類型"],
    }

    for target, candidates in aliases.items():

        if target not in df.columns:

            for candidate in candidates:

                if candidate in df.columns:
                    df[target] = df[candidate]
                    break

        if target not in df.columns:

            df[target] = (
                "TWD"
                if target == "幣別"
                else ""
                if target in ["標的名稱", "資產類型"]
                else 0
            )

    from modules.data_loader import clean_number

    # 數字欄位清理
    numeric_cols = [
        "持有股數",
        "平均成本",
        "總成本",
        "即時股價",
        "即時市值",
        "未實現損益",
    ]

    for col in numeric_cols:
        df[col] = df[col].apply(clean_number)

    df["代號"] = (
        df["代號"]
        .astype(str)
        .str.strip()
    )

    df["幣別"] = (
        df["幣別"]
        .fillna("TWD")
        .replace("", "TWD")
    )

    # 移除空白標的
    df = df[
        df["代號"].ne("")
        & df["代號"].str.lower().ne("nan")
    ]

    return df.reset_index(drop=True)

def normalize_capital(df):
    """
    Capital 支援：
    1. 直向：項目類別、金額、年利率、質押市值
    2. 橫向：第一列為欄位名稱，其餘每欄一筆資料
    """
    if df.empty:
        return pd.DataFrame(
            columns=["項目類別", "金額", "年利率", "質押市值"]
        )

    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    if str(df.iloc[0, 0]).strip() in [
        "項目類別", "項目", "名稱"
    ]:
        return df

    first = str(df.iloc[0, 0]).strip()

    if first in ["欄位", "項目"]:
        df.columns = df.iloc[0].astype(str)
        df = df.iloc[1:].set_index(df.columns[0]).T.reset_index()

    return df


def load_cashflow(df):
    from modules.config import DEFAULT_CASHFLOW

    result = DEFAULT_CASHFLOW.copy()

    if df.empty:
        return result

    for _, row in df.iterrows():
        if len(row) < 2:
            continue

        key = str(row.iloc[0]).strip()

        if key in result:
            result[key] = clean_number(row.iloc[1])

    return result