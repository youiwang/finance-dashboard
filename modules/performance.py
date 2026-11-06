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

    days = (dates - dates.min()).days / 365.0

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


def _pick_column(df, candidates):
    for col in candidates:
        if col in df.columns:
            return col
    return None


def _normalize_trade_type(value):
    text = str(value).strip().lower()

    if text in ["買進", "買入", "buy", "b"]:
        return "buy"
    if text in ["賣出", "sell", "s"]:
        return "sell"
    if text in ["股息", "配息", "股利", "dividend", "interest", "息收"]:
        return "dividend"
    if text in ["手續費", "交易稅", "費用", "fee", "tax"]:
        return "fee"
    if text in ["提領", "贖回", "withdraw"]:
        return "withdraw"
    if text in ["入金", "投入", "deposit"]:
        return "deposit"

    return "other"


def _normalize_symbol(value):
    text = str(value).strip().upper()

    if text.lower() == "nan":
        return ""

    if ":" in text:
        text = text.split(":")[-1].strip()

    if text.endswith(".TW") or text.endswith(".TWO"):
        text = text.split(".")[0].strip()

    if text.endswith(".0"):
        try:
            num = int(float(text))
            text = str(num)
        except ValueError:
            return text

    if text.isdigit():
        text = text.zfill(4)

    return text


def _prepare_history(history):
    date_col = _pick_column(history, ["日期", "date"])
    type_col = _pick_column(history, ["交易類型", "類型", "type"])
    amount_col = _pick_column(history, ["金額", "成交金額", "amount"])
    quantity_col = _pick_column(history, ["股數", "數量", "持有股數", "quantity"])
    symbol_col = _pick_column(history, ["標的", "代號", "symbol"])
    currency_col = _pick_column(history, ["幣別", "currency"])

    if date_col is None or type_col is None:
        return pd.DataFrame()

    df = history.copy()
    df["日期"] = pd.to_datetime(df[date_col], errors="coerce")
    df["交易類型_標準"] = df[type_col].apply(_normalize_trade_type)

    if amount_col is not None:
        df["金額_原始"] = df[amount_col].apply(clean_number)
    else:
        price_col = _pick_column(df, ["成交價", "價格", "price"])
        if quantity_col is not None and price_col is not None:
            qty = df[quantity_col].apply(clean_number)
            price = df[price_col].apply(clean_number)
            df["金額_原始"] = qty * price
        else:
            df["金額_原始"] = 0.0

    if quantity_col is not None:
        df["股數_標準"] = df[quantity_col].apply(clean_number)
    else:
        df["股數_標準"] = 0.0

    if symbol_col is not None:
        df["代號_標準"] = df[symbol_col].apply(_normalize_symbol)
    else:
        df["代號_標準"] = ""

    if currency_col is not None:
        df["幣別_標準"] = (
            df[currency_col].astype(str).str.upper().str.strip()
        )
    else:
        df["幣別_標準"] = "TWD"

    df = df.dropna(subset=["日期"]).sort_values("日期").reset_index(drop=True)

    def to_cashflow(row):
        t = row["交易類型_標準"]
        amount = abs(clean_number(row["金額_原始"]))

        if t in ["buy", "deposit", "fee"]:
            return -amount
        if t in ["sell", "dividend", "withdraw"]:
            return amount
        return 0.0

    df["現金流"] = df.apply(to_cashflow, axis=1)

    return df


def _calculate_realized_metrics(history):
    if history.empty:
        return {
            "realized_profit": 0.0,
            "dividend_income": 0.0,
            "total_buy_amount": 0.0,
        }

    realized_profit = 0.0
    dividend_income = 0.0
    total_buy_amount = 0.0

    lots = {}

    for _, row in history.iterrows():
        symbol = row["代號_標準"]
        trade_type = row["交易類型_標準"]
        amount = abs(clean_number(row["金額_原始"]))
        quantity = max(clean_number(row["股數_標準"]), 0.0)

        if trade_type == "buy":
            total_buy_amount += amount
            if symbol and quantity > 0:
                lots.setdefault(symbol, []).append([quantity, amount / quantity])

        elif trade_type == "sell":
            if quantity <= 0:
                continue

            sell_price = amount / quantity if quantity > 0 else 0.0
            remaining = quantity
            cost = 0.0

            queue = lots.get(symbol, [])
            while remaining > 0 and queue:
                lot_qty, lot_cost = queue[0]
                used = min(lot_qty, remaining)
                cost += used * lot_cost
                lot_qty -= used
                remaining -= used

                if lot_qty <= 0:
                    queue.pop(0)
                else:
                    queue[0][0] = lot_qty

            proceeds = sell_price * quantity
            realized_profit += proceeds - cost

        elif trade_type == "dividend":
            dividend_income += amount

        elif trade_type == "fee":
            realized_profit -= amount

    return {
        "realized_profit": realized_profit,
        "dividend_income": dividend_income,
        "total_buy_amount": total_buy_amount,
        "open_position_cost": sum(
            qty * unit_cost
            for symbol_lots in lots.values()
            for qty, unit_cost in symbol_lots
        ),
    }


def _build_xirr(history, ending_value):
    if history.empty:
        return None

    cashflow_rows = history[history["現金流"] != 0].copy()
    if cashflow_rows.empty:
        return None

    cashflows = cashflow_rows["現金流"].tolist()
    dates = cashflow_rows["日期"].tolist()

    if ending_value > 0:
        last_date = max(cashflow_rows["日期"].max(), pd.Timestamp.today())
        cashflows.append(ending_value)
        dates.append(last_date)

    return calculate_xirr(cashflows, dates)


def _build_growth_data(history, ending_value):
    if history.empty:
        return pd.DataFrame()

    trend = history[["日期", "現金流"]].copy().sort_values("日期")
    trend["淨投入變動"] = -trend["現金流"]
    trend["累計投入"] = trend["淨投入變動"].cumsum()

    daily = trend.groupby("日期", as_index=False)["累計投入"].last()
    daily["投資市值"] = pd.NA

    if ending_value > 0:
        daily.loc[daily.index[-1], "投資市值"] = ending_value

    return daily


def build_positions_from_performance(history):
    cleaned_history = _prepare_history(history)

    columns = [
        "代號",
        "標的名稱",
        "持有股數",
        "平均成本",
        "總成本",
        "即時股價",
        "即時市值",
        "未實現損益",
        "幣別",
        "資產類型",
    ]

    if cleaned_history.empty:
        return pd.DataFrame(columns=columns)

    lots = {}
    symbol_currency = {}

    for _, row in cleaned_history.iterrows():
        symbol = _normalize_symbol(row["代號_標準"])
        trade_type = row["交易類型_標準"]
        quantity = max(clean_number(row["股數_標準"]), 0.0)
        amount = abs(clean_number(row["金額_原始"]))
        currency = str(row.get("幣別_標準", "TWD")).upper().strip()

        if not symbol:
            continue

        if symbol not in symbol_currency:
            symbol_currency[symbol] = currency if currency else "TWD"

        if trade_type == "buy" and quantity > 0:
            unit_cost = amount / quantity if quantity > 0 else 0.0
            lots.setdefault(symbol, []).append([quantity, unit_cost])

        elif trade_type == "sell" and quantity > 0:
            queue = lots.get(symbol, [])
            remaining = quantity

            while remaining > 0 and queue:
                lot_qty, lot_cost = queue[0]
                used = min(lot_qty, remaining)
                lot_qty -= used
                remaining -= used

                if lot_qty <= 0:
                    queue.pop(0)
                else:
                    queue[0][0] = lot_qty

    rows = []

    for symbol, queue in lots.items():
        total_qty = sum(q for q, _ in queue)
        total_cost = sum(q * c for q, c in queue)

        if total_qty <= 0 and total_cost <= 0:
            continue

        avg_cost = total_cost / total_qty if total_qty > 0 else 0.0

        rows.append({
            "代號": symbol,
            "標的名稱": "",
            "持有股數": total_qty,
            "平均成本": avg_cost,
            "總成本": total_cost,
            "即時股價": 0.0,
            "即時市值": 0.0,
            "未實現損益": 0.0,
            "幣別": symbol_currency.get(symbol, "TWD"),
            "資產類型": "股票",
        })

    if not rows:
        return pd.DataFrame(columns=columns)

    return pd.DataFrame(rows)[columns]


def merge_portfolio_overrides(base_positions, manual_portfolio):
    columns = [
        "代號",
        "標的名稱",
        "持有股數",
        "平均成本",
        "總成本",
        "即時股價",
        "即時市值",
        "未實現損益",
        "幣別",
        "資產類型",
    ]

    base = (
        base_positions.copy()
        if isinstance(base_positions, pd.DataFrame)
        else pd.DataFrame(columns=columns)
    )
    manual = (
        manual_portfolio.copy()
        if isinstance(manual_portfolio, pd.DataFrame)
        else pd.DataFrame(columns=columns)
    )

    for frame in [base, manual]:
        for col in columns:
            if col not in frame.columns:
                frame[col] = 0.0 if col in [
                    "持有股數", "平均成本", "總成本", "即時股價", "即時市值", "未實現損益"
                ] else ""
        frame["代號"] = frame["代號"].apply(_normalize_symbol)
        frame["幣別"] = frame["幣別"].replace("", "TWD")

    manual = manual[
        manual["代號"].astype(str).str.strip().ne("")
        & manual["代號"].astype(str).str.lower().ne("nan")
    ].copy()

    merged = base.set_index("代號", drop=False)
    manual_indexed = manual.set_index("代號", drop=False)

    text_override_cols = ["標的名稱", "幣別", "資產類型"]
    numeric_override_cols = ["即時股價", "即時市值"]

    for symbol, row in manual_indexed.iterrows():
        if symbol not in merged.index:
            merged.loc[symbol, columns] = row[columns]
            continue

        for col in text_override_cols:
            value = str(row.get(col, "")).strip()
            if value:
                merged.at[symbol, col] = value

        for col in numeric_override_cols:
            value = clean_number(row.get(col, 0))
            if value > 0:
                merged.at[symbol, col] = value

    merged = merged.reset_index(drop=True)

    for col in ["持有股數", "平均成本", "總成本", "即時股價", "即時市值", "未實現損益"]:
        merged[col] = merged[col].apply(clean_number)

    merged["代號"] = merged["代號"].apply(_normalize_symbol)
    merged["幣別"] = merged["幣別"].replace("", "TWD")

    merged = merged[
        merged["代號"].astype(str).str.strip().ne("")
        & merged["代號"].astype(str).str.lower().ne("nan")
    ].copy()

    return merged[columns].reset_index(drop=True)


def show_performance_dashboard(data, portfolio, metrics):
    st.header("📈 投資績效")

    history = data.get("performance", pd.DataFrame())

    if history.empty:
        st.info(
            "尚未建立投資歷史紀錄。"
            "請在 Performance（Trade Log / 下單紀錄）工作表新增交易資料。"
        )
        return

    cleaned_history = _prepare_history(history)

    if cleaned_history.empty:
        st.warning("Performance（Trade Log / 下單紀錄）欄位尚未符合規格。")
        return

    realized = _calculate_realized_metrics(cleaned_history)

    investment_assets = clean_number(metrics.get("investment_assets", 0))
    investment_cost = clean_number(metrics.get("investment_cost", 0))
    open_position_cost = clean_number(
        realized.get("open_position_cost", 0)
    )

    ending_value = (
        investment_assets
        if investment_assets > 0
        else open_position_cost
    )

    unrealized_cost_base = (
        investment_cost
        if investment_cost > 0
        else open_position_cost
    )

    unrealized_profit = ending_value - unrealized_cost_base
    unrealized_return = (
        unrealized_profit / unrealized_cost_base
        if unrealized_cost_base > 0 else 0
    )

    xirr = _build_xirr(cleaned_history, ending_value)

    k1, k2, k3, k4 = st.columns(4)
    if investment_assets > 0:
        k1.metric("投資總市值", f"NT$ {ending_value:,.0f}")
    else:
        k1.metric("投資總市值(估算)", f"NT$ {ending_value:,.0f}")
    k2.metric("累計投入成本", f"NT$ {realized['total_buy_amount']:,.0f}")
    k3.metric("未實現損益", f"NT$ {unrealized_profit:,.0f}")
    k4.metric("未實現報酬率", f"{unrealized_return * 100:,.2f}%")

    k5, k6, k7, k8 = st.columns(4)
    k5.metric("已實現損益", f"NT$ {realized['realized_profit']:,.0f}")
    k6.metric("累計股息收入", f"NT$ {realized['dividend_income']:,.0f}")
    k7.metric(
        "整體年化報酬率(XIRR)",
        f"{xirr * 100:,.2f}%" if xirr is not None else "N/A"
    )
    k8.metric("報價更新", pd.Timestamp.now().strftime("%Y/%m/%d %H:%M"))

    if investment_assets <= 0 and ending_value > 0:
        st.caption(
            "目前未取得即時持倉市值，"
            "已先以歷史交易推算的期末持倉成本做估算。"
        )

    if not portfolio.empty:
        st.subheader("投資組合配置")
        pie_data = portfolio[portfolio["台幣市值"] > 0].copy()

        if not pie_data.empty:
            allocation = (
                pie_data.groupby("代號", as_index=False)["台幣市值"]
                .sum()
                .sort_values("台幣市值", ascending=False)
            )
            st.bar_chart(
                allocation.set_index("代號")["台幣市值"],
                width="stretch"
            )

    growth_data = _build_growth_data(cleaned_history, ending_value)
    if not growth_data.empty:
        st.subheader("資產成長趨勢")
        trend_chart = growth_data.set_index("日期")[
            ["累計投入", "投資市值"]
        ].dropna(how="all")

        if not trend_chart.empty:
            st.line_chart(
                trend_chart,
                width="stretch"
            )

    if not portfolio.empty:
        st.subheader("個股績效排名")
        ranking_cols = [
            "代號",
            "標的名稱",
            "台幣市值",
            "台幣成本",
            "台幣損益",
            "報酬率",
        ]

        ranking = portfolio[ranking_cols].copy()
        ranking = ranking[
            ranking["代號"].astype(str).str.strip().ne("")
            & ranking["代號"].astype(str).str.strip().ne("0000")
            & (
                (ranking["台幣市值"] > 0)
                | (ranking["台幣成本"] > 0)
            )
        ].copy()

        if ranking.empty:
            st.info("目前沒有可排名的有效持倉資料。")
        else:
            total_market_value = ranking["台幣市值"].sum()

            if total_market_value > 0:
                ranking["市值占比"] = (
                    ranking["台幣市值"] / total_market_value * 100
                )
            else:
                ranking["市值占比"] = 0.0

            ranking = ranking.sort_values(
                by=["台幣損益", "報酬率"],
                ascending=False
            ).reset_index(drop=True)

            st.dataframe(
                ranking,
                width="stretch",
                hide_index=True
            )

    st.subheader("歷史投資現金流")
    display_cols = [
        "日期",
        "代號_標準",
        "交易類型_標準",
        "股數_標準",
        "金額_原始",
        "現金流",
        "幣別_標準",
    ]

    history_display = cleaned_history[display_cols].rename(columns={
        "代號_標準": "代號",
        "交易類型_標準": "交易類型",
        "股數_標準": "股數",
        "金額_原始": "交易金額",
        "幣別_標準": "幣別",
    })

    history_display["日期"] = history_display["日期"].dt.strftime("%Y-%m-%d")
    history_display["代號"] = history_display["代號"].astype(str)
    history_display["交易類型"] = history_display["交易類型"].astype(str)
    history_display["幣別"] = history_display["幣別"].astype(str)
    history_display["股數"] = pd.to_numeric(
        history_display["股數"], errors="coerce"
    ).fillna(0.0)
    history_display["交易金額"] = pd.to_numeric(
        history_display["交易金額"], errors="coerce"
    ).fillna(0.0)
    history_display["現金流"] = pd.to_numeric(
        history_display["現金流"], errors="coerce"
    ).fillna(0.0)

    st.dataframe(
        history_display.sort_values("日期", ascending=False),
        width="stretch",
        hide_index=True
    )

    with st.expander("🛠️ Debug：績效計算與報價來源"):
        debug_col1, debug_col2, debug_col3 = st.columns(3)
        debug_col1.metric("metrics 投資市值", f"NT$ {investment_assets:,.0f}")
        debug_col2.metric("估算期末價值", f"NT$ {ending_value:,.0f}")
        debug_col3.metric("期末持倉成本", f"NT$ {open_position_cost:,.0f}")

        if not portfolio.empty:
            debug_cols = [
                "代號",
                "持有股數",
                "平均成本",
                "總成本",
                "最新價格",
                "台幣市值",
                "台幣成本",
                "報價來源",
                "報價代號",
                "候選代號",
                "市值來源",
            ]
            available_debug_cols = [
                col for col in debug_cols if col in portfolio.columns
            ]
            debug_df = portfolio[available_debug_cols].copy()

            for col in ["代號", "報價來源", "報價代號", "候選代號", "市值來源"]:
                if col in debug_df.columns:
                    debug_df[col] = debug_df[col].astype(str)

            st.dataframe(
                debug_df.sort_values("台幣市值", ascending=False),
                width="stretch",
                hide_index=True
            )

            zero_value_count = int((portfolio["台幣市值"] <= 0).sum())
            st.caption(
                f"台幣市值 <= 0 的標的數：{zero_value_count}"
            )

        st.write("交易類型統計")
        st.dataframe(
            cleaned_history["交易類型_標準"]
            .value_counts(dropna=False)
            .rename_axis("交易類型")
            .reset_index(name="筆數"),
            width="stretch",
            hide_index=True
        )