SHEET_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1WvqwEcs-k92EXw90P_6hY5bqgZgA3jyMDFNSQZbP3AA/edit"
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

DEFAULT_CASHFLOW = {
    "每月薪資收入": 80000,
    "其他收入": 0,
    "每月被動收入": 0,
    "每月生活費": 40000,
    "每月貸款還款": 15000,
    "每月信用卡支出": 0,
    "其他固定支出": 0,
}

# 標的名稱含有正2，或代號含有 L 時，
# 以兩倍曝險估算。其他標的預設一倍。
DEFAULT_LEVERAGE = 2.0

# 只有確認實際追蹤標的後才應修改。
LEVERAGE_OVERRIDES = {}

RISK_THRESHOLDS = {
    "pledge_warning": 200,
    "pledge_danger": 166,
    "debt_warning": 50,
}