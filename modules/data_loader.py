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

SHEET_ALIASES = {
    "performance": ["Performance", "Trade Log", "下單紀錄", "交易紀錄"],
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
    conn = get_connection()
    sheet_candidates = SHEET_ALIASES.get(
        name, [SHEETS[name]]
    )
    last_error = None

    for worksheet_name in sheet_candidates:
        try:
            df = conn.read(
                spreadsheet=SHEET_URL,
                worksheet=worksheet_name,
                ttl=0
            )

            if df is None:
                continue

            return df.dropna(how="all").reset_index(drop=True)

        except Exception as e:
            last_error = e
            continue

    if required:
        st.error(f"讀取 {name} 工作表失敗：{last_error}")
        st.stop()

    if name == "performance":
        st.warning(
            "工作表 Performance / Trade Log / 下單紀錄 尚未建立或無法讀取。"
        )
    else:
        st.warning(
            f"工作表 {SHEETS[name]} 尚未建立或無法讀取。"
        )
    return pd.DataFrame()


def _normalize_portfolio_symbol(value):
    text = str(value).strip().upper()
    if not text or text.lower() == "nan":
        return ""

    if ":" in text:
        text = text.split(":")[-1].strip()

    if text.endswith(".TW") or text.endswith(".TWO"):
        text = text.split(".")[0].strip()

    if text.endswith(".0"):
        try:
            text = str(int(float(text)))
        except ValueError:
            return text

    if text.isdigit():
        text = text.zfill(4)

    return text


def _apply_portfolio_aliases(df):
    aliases = {
        "代號": ["代號", "股票代號", "代碼", "symbol"],
        "標的名稱": ["標的名稱", "名稱", "name"],
        "持有股數": ["持有股數", "持有數量", "股數", "quantity"],
        "平均成本": ["平均成本", "成本", "cost"],
        "總成本": ["總成本", "持有成本"],
        "即時股價": ["即時股價", "目前股價", "股價", "price"],
        "即時市值": ["即時市值", "市值", "market_value"],
        "未實現損益": ["未實現損益", "損益", "pnl"],
        "幣別": ["幣別", "Currency", "currency"],
        "資產類型": ["資產類型", "類型", "asset_type"],
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

    return df


def _clean_portfolio_rows(df):
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

    df["代號"] = df["代號"].apply(_normalize_portfolio_symbol)
    df["標的名稱"] = df["標的名稱"].astype(str).replace("nan", "")
    df["幣別"] = df["幣別"].fillna("TWD").replace("", "TWD")

    invalid = {"", "NAN", "NONE", "0", "0000"}
    df = df[~df["代號"].isin(invalid)].copy()

    df = df[
        (df["持有股數"] > 0)
        | (df["總成本"] > 0)
        | (df["即時市值"] > 0)
        | (df["即時股價"] > 0)
    ].copy()

    return df.reset_index(drop=True)


def _normalize_portfolio_column_format(df):
    first_col = df.columns[0]
    df[first_col] = df[first_col].astype(str).str.strip()
    df = df.set_index(first_col).T
    df.index.name = "原始欄位"
    df = df.reset_index(drop=True)
    df.columns = [str(c).strip() for c in df.columns]

    df = _apply_portfolio_aliases(df)
    return _clean_portfolio_rows(df)


def _normalize_portfolio_row_format(df):
    df.columns = [str(c).strip() for c in df.columns]
    df = _apply_portfolio_aliases(df)
    return _clean_portfolio_rows(df)


def normalize_portfolio(df):
    """
    Portfolio 支援：
    1. 直向欄位格式：第一欄是欄位名稱，後面是各標的（舊版）
    2. 標準列表格式：每列一個標的（新版）
    """
    if df.empty:
        return pd.DataFrame()

    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    row_format_markers = {"代號", "持有股數", "平均成本", "總成本"}
    marker_count = len(row_format_markers.intersection(set(df.columns)))

    if marker_count >= 2:
        return _normalize_portfolio_row_format(df)

    return _normalize_portfolio_column_format(df)


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