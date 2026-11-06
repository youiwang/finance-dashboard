# 個人投資儀表板 (Personal Finance Dashboard)

這是一個基於 [Streamlit](https://streamlit.io/) 開發的個人投資與財務管理儀表板。透過整合 Google Sheets 的個人資產數據以及 Yahoo Finance、FRED 的總體經濟數據，提供即時的資產狀態監控與動態投資策略建議。

## 功能特色 (Features)

- **個人資產監控**：透過 Google Sheets 即時讀取持股部位 (Portfolio) 與資金狀態 (Capital)。
- **市場景氣指標**：自動抓取 VIX 恐慌指數與 S&P 500 回檔幅度 (Drawdown)。
- **動態曝險策略**：根據市場狀態 (如 VIX 數值與大盤回檔幅度)，提供基於 CLEC 4:4:2 基準的動態資金配置與加碼建議。
- **風險控管與財務健康度**：
  - 計算淨資產 (Net Worth) 與總資產。
  - 監控資產負債比 (Leverage Ratio)。
  - 追蹤股票質押維持率 (Maintenance Margin)，並在低於安全水位時發出警告。
  - 評估還款負擔率與應急準備金存量。

## 系統需求 (Requirements)

請確保您的環境已安裝 Python，並安裝以下依賴套件：

```bash
pip install streamlit yfinance pandas-datareader st-gsheets-connection
```

````

## 使用方式 (Usage)

1. **設定 Google Sheets**：
   - 準備一個包含 `Portfolio` 與 `Capital` 兩個工作表的 Google Sheet。
   - 確保該 Google Sheet 的權限設定為「知道連結的人均可檢視」，或設定好 Streamlit 的 Google Sheets 驗證金鑰。
   - 在 `app.py` 中更新 `spreadsheet_url` 為您的 Google Sheet 連結。

2. **啟動應用程式**：
   在終端機中執行以下指令來啟動 Streamlit 伺服器：

   ```bash
   streamlit run app.py
   ```

3. **瀏覽儀表板**：
   啟動後，瀏覽器會自動開啟 `http://localhost:8501` 顯示您的個人投資儀表板。

## 檔案結構 (File Structure)

- `app.py`: 儀表板的主程式碼，包含 UI 佈局、資料抓取與邏輯計算。

## 策略邏輯參考

本儀表板的動態曝險建議參考了特定的投資策略邏輯（例如 Podcast 提及的 CLEC 4:4:2 基準）：

- **極度恐慌 (VIX > 40)**：全面動用現金加碼。
- **深度崩盤 (回檔 > 40%)**：將原型 ETF 轉入槓桿 ETF 放大底部曝險。
- **市場狂熱 (VIX < 15)**：獲利了結槓桿部位，恢復標準配置。
````
