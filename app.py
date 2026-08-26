import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import datetime
import urllib.parse
import os
import streamlit.components.v1 as components

# 1. Page Configuration
st.set_page_config(
    page_title="SwingPro | AI Swing Trader & Journal",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

JOURNAL_FILE = "trade_journal.csv"

# Nifty 50 Liquid Watchlist
WATCHLIST = [
    "ADANIENT.NS", "ADANIPORTS.NS", "APOLLOHOSP.NS", "ASIANPAINT.NS", "AXISBANK.NS",
    "BAJAJ-AUTO.NS", "BAJFINANCE.NS", "BAJAJFINSV.NS", "BPCL.NS", "BHARTIARTL.NS",
    "BRITANNIA.NS", "CIPLA.NS", "COALINDIA.NS", "DIVISLAB.NS", "DRREDDY.NS",
    "EICHERMOT.NS", "GRASIM.NS", "HCLTECH.NS", "HDFCBANK.NS", "HDFCLIFE.NS",
    "HEROMOTOCO.NS", "HINDALCO.NS", "HINDUNILVR.NS", "ICICIBANK.NS", "ITC.NS",
    "INDUSINDBK.NS", "INFY.NS", "JSWSTEEL.NS", "KOTAKBANK.NS", "LT.NS",
    "M&M.NS", "MARUTI.NS", "NTPC.NS", "NESTLEIND.NS", "ONGC.NS",
    "POWERGRID.NS", "RELIANCE.NS", "SBILIFE.NS", "SBIN.NS", "SUNPHARMA.NS",
    "TCS.NS", "TATACONSUM.NS", "TATAMOTORS.NS", "TATASTEEL.NS", "TECHM.NS",
    "TITAN.NS", "ULTRACEMCO.NS", "WIPRO.NS"
]

# 2. Sidebar - Professional Risk Calculator
st.sidebar.markdown("### 💼 **Portfolio & Risk Engine**")
total_capital = st.sidebar.number_input("Total Capital (₹)", min_value=10000, value=100000, step=5000)
risk_pct = st.sidebar.slider("Risk Per Trade (%)", min_value=0.5, max_value=3.0, value=1.0, step=0.25) / 100
rr_ratio = st.sidebar.slider("Risk-to-Reward Ratio (1:X)", min_value=1.5, max_value=4.0, value=2.0, step=0.5)

st.sidebar.markdown("---")
max_risk_amount = round(total_capital * risk_pct, 2)
st.sidebar.metric("🛡️ Max Risk Per Trade", f"₹{max_risk_amount}")
st.sidebar.caption("System strictly limits position size to keep losses bounded.")

# 3. Technical Indicator Computation
def calculate_indicators(df):
    df["EMA_20"] = df["Close"].ewm(span=20, adjust=False).mean()
    df["EMA_50"] = df["Close"].ewm(span=50, adjust=False).mean()
    
    delta = df["Close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / (loss + 1e-9)
    df["RSI"] = 100 - (100 / (1 + rs))
    return df

# 4. Scanner Function (Batch Engine)
def run_swing_scanner():
    results = []
    with st.spinner("⚡ Scanning Nifty 50 with Institutional Filters..."):
        try:
            data = yf.download(WATCHLIST, period="6mo", interval="1d", group_by="ticker", threads=True, progress=False)
        except Exception as e:
            st.error(f"Error fetching market data: {e}")
            return []

    for ticker in WATCHLIST:
        try:
            if ticker not in data.columns.levels[0]:
                continue
            df = data[ticker].dropna().copy()
            if len(df) < 55:
                continue

            df = calculate_indicators(df)
            latest = df.iloc[-1]
            
            cmp_price = float(latest["Close"])
            ema20 = float(latest["EMA_20"])
            ema50 = float(latest["EMA_50"])
            rsi = float(latest["RSI"])

            # Strategy Criteria: EMA Trend Alignment & RSI Momentum
            if ema20 > ema50 and rsi > 55:
                entry = round(cmp_price, 2)
                swing_low = round(float(df["Low"].tail(7).min()), 2)
                risk_per_share = entry - swing_low

                if risk_per_share > 0:
                    target = round(entry + (rr_ratio * risk_per_share), 2)
                    max_risk = total_capital * risk_pct
                    qty = int(max_risk / risk_per_share)

                    if qty > 0:
                        results.append({
                            "Ticker": ticker,
                            "Stock": ticker.replace(".NS", ""),
                            "CMP": entry,
                            "StopLoss": swing_low,
                            "Target": target,
                            "Qty": qty,
                            "HoldingPeriod": "1 - 3 Weeks",
                            "TotalCapital": round(qty * entry, 2),
                            "RiskAmount": round(qty * risk_per_share, 2),
                            "RSI": round(rsi, 2)
                        })
        except Exception:
            continue

    return results

# 5. Journal Operations
def save_to_journal(trade_data):
    row = pd.DataFrame([{
        "Date": datetime.date.today().strftime("%Y-%m-%d"),
        "Stock": trade_data["Stock"],
        "Entry_CMP": trade_data["CMP"],
        "Stop_Loss": trade_data["StopLoss"],
        "Target": trade_data["Target"],
        "Qty": trade_data["Qty"],
        "Capital_Allocated": trade_data["TotalCapital"],
        "Status": "OPEN"
    }])
    if not os.path.exists(JOURNAL_FILE):
        row.to_csv(JOURNAL_FILE, index=False)
    else:
        row.to_csv(JOURNAL_FILE, mode='a', header=False, index=False)

# 6. Main UI Layout
tabs = st.tabs(["🚀 Live Scanner", "📓 Trade Journal", "📚 Trading Playbook & Checklist"])

# TAB 1: Live Scanner
with tabs[0]:
    col_t1, col_t2 = st.columns([3, 1])
    with col_t1:
        st.subheader("🎯 High-Probability Swing Setups")
        st.caption("Strategy: 20 EMA > 50 EMA | RSI Momentum > 55 | Dynamic 7-Day Swing-Low SL")
    with col_t2:
        scan_btn = st.button("🔄 Scan Market Now", type="primary", use_container_width=True)

    if scan_btn or "scanned_trades" in st.session_state:
        if scan_btn:
            st.session_state.scanned_trades = run_swing_scanner()
        
        trades = st.session_state.get("scanned_trades", [])
        
        if trades:
            st.success(f"✨ Found {len(trades)} Qualified Swing Setups!")
            
            for idx, trade in enumerate(trades):
                with st.container():
                    st.markdown(f"### 📌 **{trade['Stock']}** &nbsp; `RSI: {trade['RSI']}`")
                    
                    # Responsive Clean Metric Display
                    m1, m2, m3, m4, m5 = st.columns(5)
                    m1.markdown(f"**CMP / Entry**<br><span style='font-size:1.3rem;font-weight:bold;color:#007BFF;'>₹{trade['CMP']}</span>", unsafe_allow_html=True)
                    m2.markdown(f"**Stop Loss**<br><span style='font-size:1.3rem;font-weight:bold;color:#DC3545;'>₹{trade['StopLoss']}</span>", unsafe_allow_html=True)
                    m3.markdown(f"**Target (1:{rr_ratio})**<br><span style='font-size:1.3rem;font-weight:bold;color:#28A745;'>₹{trade['Target']}</span>", unsafe_allow_html=True)
                    m4.markdown(f"**Safe Qty**<br><span style='font-size:1.3rem;font-weight:bold;'>{trade['Qty']} Shares</span>", unsafe_allow_html=True)
                    m5.markdown(f"**Holding**<br><span style='font-size:1.1rem;'>{trade['HoldingPeriod']}</span>", unsafe_allow_html=True)
                    
                    st.write("")
                    
                    # Action Bar: WhatsApp & Journal Buttons
                    b_col1, b_col2 = st.columns([1, 1])
                    
                    with b_col1:
                        single_msg = (
                            f"🚀 *Swing Trade Setup: {trade['Stock']}*\n\n"
                            f"• *CMP / Entry:* ₹{trade['CMP']}\n"
                            f"• *Stop Loss:* ₹{trade['StopLoss']}\n"
                            f"• *Target (1:{rr_ratio}):* ₹{trade['Target']}\n"
                            f"• *Safe Qty:* {trade['Qty']} shares\n"
                            f"• *Expected Holding:* {trade['HoldingPeriod']}\n"
                            f"• *Capital Required:* ₹{trade['TotalCapital']}\n"
                            f"• *Max Risk:* ₹{trade['RiskAmount']}\n\n"
                            f"⚠️ _Trade with discipline & strict SL!_"
                        )
                        wa_url = f"https://api.whatsapp.com/send?text={urllib.parse.quote(single_msg)}"
                        st.markdown(
                            f'<a href="{wa_url}" target="_blank">'
                            f'<button style="background-color:#25D366;color:white;width:100%;padding:8px;border:none;border-radius:6px;cursor:pointer;font-weight:bold;">📲 Share on WhatsApp</button>'
                            f'</a>',
                            unsafe_allow_html=True
                        )
                        
                    with b_col2:
                        if st.button(f"➕ Add {trade['Stock']} to Journal", key=f"j_{idx}", use_container_width=True):
                            save_to_journal(trade)
                            st.toast(f"✅ {trade['Stock']} saved to Trade Journal!")

                    # TradingView Chart Embed in Expander
                    with st.expander(f"📊 View Interactive Live Chart for {trade['Stock']}"):
                        tv_symbol = f"NSE:{trade['Stock']}"
                        tv_html = f"""
                        <div class="tradingview-widget-container" style="height:400px;width:100%">
                          <iframe src="https://s.tradingview.com/widgetembed/?frameElementId=tradingview_widget&symbol={tv_symbol}&interval=D&hidesidetoolbar=1&symboledit=1&saveimage=1&toolbarbg=f1f3f6&studies=[]&theme=light&style=1&timezone=Asia%2FKolkata" style="width: 100%; height: 400px; border: 0;"></iframe>
                        </div>
                        """
                        components.html(tv_html, height=410)
                        
                    st.divider()
        else:
            st.info("Scanner execution completed. No trade setup matching current criteria.")

# TAB 2: Trade Journal
with tabs[1]:
    st.subheader("📓 Trade Management Journal")
    st.caption("Track your executed trades and download performance logs.")
    
    if os.path.exists(JOURNAL_FILE):
        j_df = pd.read_csv(JOURNAL_FILE)
        st.dataframe(j_df, use_container_width=True)
        
        csv_data = j_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Journal as CSV",
            data=csv_data,
            file_name=f"trade_journal_{datetime.date.today()}.csv",
            mime="text/csv"
        )
    else:
        st.info("Journal is currently empty. Click '➕ Add to Journal' on any trade setup to record it here.")

# TAB 3: Strategy Playbook & Checklist
with tabs[2]:
    st.subheader("📚 Pro Swing Trading Playbook")
    
    st.markdown("""
    ### 🛡️ **Core Principles of Swing Trading**
    * **1% Rule:** Never risk more than 1% of your total capital on a single setup.
    * **Asymmetrical Risk-to-Reward:** Always target at least $1:2$. A 50% win rate generates solid alpha when losses are small and winners run.
    * **Trend Alignment:** Only enter long positions when 20 EMA is comfortably above 50 EMA.
    """)
    
    st.markdown("---")
    st.subheader("📋 Pre-Trade Mental Checklist")
    st.checkbox("1. 20 EMA is above 50 EMA on Daily Chart (Uptrend confirmed)")
    st.checkbox("2. RSI is above 55 (Strong bullish momentum)")
    st.checkbox("3. Stop loss is strictly placed at the recent 7-day swing low")
    st.checkbox("4. Position size is calculated using the 1% risk rule, not gut feeling")
    st.checkbox("5. I accept the loss beforehand if the stop loss gets triggered")
