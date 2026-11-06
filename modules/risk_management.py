import streamlit as st


def show_risk_dashboard(metrics):
    st.header("🛡️ 槓桿與風險管理")

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "CLEC 曝險槓桿倍率",
        f'{metrics["exposure_ratio"]:.2f}x'
    )

    col2.metric(
        "資產負債比",
        f'{metrics["debt_ratio"] * 100:.1f}%'
    )

    col3.metric(
        "股票質押維持率",
        (
            f'{metrics["maintenance_margin"] * 100:.1f}%'
            if metrics["maintenance_margin"] > 0
            else "未使用"
        )
    )

    st.subheader("📊 投資風險分析")

    if metrics["exposure_ratio"] > 2:
        st.error("曝險倍率超過 2 倍，請重新評估投資風險。")

    elif metrics["exposure_ratio"] > 1.5:
        st.warning("目前曝險偏高，建議檢查槓桿配置。")

    else:
        st.success("目前曝險倍率未超過 1.5 倍。")

    if metrics["debt_ratio"] > 0.5:
        st.warning("資產負債比超過 50%，建議留意負債風險。")

    margin = metrics["maintenance_margin"] * 100

    if margin > 0:
        if margin < 166:
            st.error(
                f"🚨 質押維持率 {margin:.1f}%，"
                "已進入高風險區域。"
            )

        elif margin < 200:
            st.warning(
                f"⚠️ 質押維持率 {margin:.1f}%，"
                "建議增加安全緩衝。"
            )

        else:
            st.success(
                f"質押維持率 {margin:.1f}%，"
                "目前高於 200%。"
            )

    st.caption(
        "曝險倍率是簡化估算，槓桿 ETF 的每日曝險會隨價格與再平衡改變。"
    )