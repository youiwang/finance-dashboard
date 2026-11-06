import pandas as pd

from modules.data_loader import clean_number


def calculate_financial_metrics(
    data,
    portfolio,
    crypto
):
    capital = data["capital"].copy()
    property_df = data["property"].copy()
    cashflow = data["cashflow"]

    if "項目類別" not in capital.columns:
        capital["項目類別"] = ""

    if "金額" not in capital.columns:
        capital["金額"] = 0

    if "質押市值" not in capital.columns:
        capital["質押市值"] = 0

    capital["金額"] = capital["金額"].apply(clean_number)
    capital["質押市值"] = capital["質押市值"].apply(clean_number)

    # 現金與其他 Capital 正資產
    cash_assets = capital.loc[
        capital["金額"] > 0, "金額"
    ].sum()

    # Capital 負債
    capital_liabilities = abs(
        capital.loc[
            capital["金額"] < 0, "金額"
        ].sum()
    )

    # 股票
    stock_assets = (
        portfolio["台幣市值"].sum()
        if not portfolio.empty else 0
    )

    investment_cost = (
        portfolio["台幣成本"].sum()
        if not portfolio.empty else 0
    )

    stock_exposure = (
        portfolio["實質曝險"].sum()
        if not portfolio.empty else 0
    )

    # 加密貨幣
    crypto_assets = (
        crypto["台幣市值"].sum()
        if not crypto.empty else 0
    )

    crypto_cost = (
        crypto["台幣成本"].sum()
        if not crypto.empty else 0
    )

    # 房地產
    property_value = 0
    property_debt = 0
    credit_limit = 0
    credit_used = 0

    if not property_df.empty:
        for _, row in property_df.iterrows():
            item = str(row.get("項目", "")).strip()
            amount = clean_number(row.get("金額", 0))

            if item == "房屋估值":
                property_value += amount

            elif item == "房貸剩餘本金":
                property_debt += abs(amount)

            elif item == "理財型房貸核准額度":
                credit_limit += amount

            elif item == "理財型房貸已動用":
                credit_used += amount

    available_credit = max(
        credit_limit - credit_used, 0
    )

    # 已動用額度屬於負債
    property_debt += credit_used

    # 投資資產
    investment_assets = stock_assets + crypto_assets

    # 總資產
    total_assets = (
        cash_assets
        + stock_assets
        + crypto_assets
        + property_value
    )

    # 總負債
    total_liabilities = (
        capital_liabilities + property_debt
    )

    # 淨資產
    net_worth = total_assets - total_liabilities

    # 曝險：股票槓桿曝險 + Crypto 一倍曝險
    total_exposure = (
        stock_exposure + crypto_assets
    )

    exposure_ratio = (
        total_exposure / net_worth
        if net_worth > 0 else 0
    )

    debt_ratio = (
        total_liabilities / total_assets
        if total_assets > 0 else 0
    )

    # 質押維持率
    pledge = capital[
        capital["項目類別"].astype(str).str.contains(
            "質押|融資", na=False
        )
    ]

    pledge_loans = abs(pledge["金額"].sum())
    pledge_value = pledge["質押市值"].sum()

    maintenance_margin = (
        pledge_value / pledge_loans
        if pledge_loans > 0 else 0
    )

    # 每月現金流
    income = (
        cashflow["每月薪資收入"]
        + cashflow["其他收入"]
    )

    passive_income = cashflow["每月被動收入"]

    living = cashflow["每月生活費"]
    loan_payment = cashflow["每月貸款還款"]
    credit_card = cashflow["每月信用卡支出"]
    other_expenses = cashflow["其他固定支出"]

    expenses = (
        living + loan_payment
        + credit_card + other_expenses
    )

    net_cashflow = income - expenses

    savings_rate = (
        net_cashflow / income
        if income > 0 else 0
    )

    debt_service_ratio = (
        loan_payment / income
        if income > 0 else 0
    )

    financial_independence = (
        passive_income / expenses
        if expenses > 0 else 0
    )

    emergency_months = (
        cash_assets / living
        if living > 0 else 0
    )

    short_term_liabilities = (
        capital_liabilities + property_debt
    )

    # 現金流動性
    cash_liquidity = (
        cash_assets / (short_term_liabilities + living)
        if short_term_liabilities + living > 0 else 0
    )

    reserve_liquidity = (
        (cash_assets + available_credit)
        / short_term_liabilities
        if short_term_liabilities > 0 else 0
    )

    total_liquidity = (
        (
            cash_assets
            + available_credit
            + stock_assets
        ) / short_term_liabilities
        if short_term_liabilities > 0 else 0
    )

    return {
        "cash_assets": cash_assets,
        "stock_assets": stock_assets,
        "crypto_assets": crypto_assets,
        "property_value": property_value,
        "investment_assets": investment_assets,
        "investment_cost": investment_cost + crypto_cost,
        "total_assets": total_assets,
        "total_liabilities": total_liabilities,
        "net_worth": net_worth,
        "total_exposure": total_exposure,
        "exposure_ratio": exposure_ratio,
        "debt_ratio": debt_ratio,
        "maintenance_margin": maintenance_margin,
        "pledge_loans": pledge_loans,
        "pledge_value": pledge_value,
        "available_credit": available_credit,
        "income": income,
        "passive_income": passive_income,
        "expenses": expenses,
        "net_cashflow": net_cashflow,
        "savings_rate": savings_rate,
        "debt_service_ratio": debt_service_ratio,
        "financial_independence": financial_independence,
        "emergency_months": emergency_months,
        "cash_liquidity": cash_liquidity,
        "reserve_liquidity": reserve_liquidity,
        "total_liquidity": total_liquidity,
    }