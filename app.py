import streamlit as st
from streamlit_gsheets import GSheetsConnection

st.title("個人投資儀表板")

# 建立與 Google Sheets 的連線
conn = st.connection("gsheets", type=GSheetsConnection)

# 讀取資料 (會自動轉為 Pandas DataFrame)
# 可以直接貼上整串 Google Sheet URL，或是使用 Spreadsheet ID
df = conn.read(
    spreadsheet="https://docs.google.com/spreadsheets/d/1WvqwEcs-k92EXw90P_6hY5bqgZgA3jyMDFNSQZbP3AA/edit?gid=0#gid=0", 
    worksheet="Portfolio" 
)

st.write("目前持股與現金部位狀態：")
st.dataframe(df)