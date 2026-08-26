import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import datetime
import urllib.parse
import os
import matplotlib.pyplot as plt

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

# 2. Sidebar - Risk Engine
st.sidebar.markdown("### 💼 **Portfolio & Risk Engine**")
total_capital = st.sidebar.number_input("Total Capital (₹)", min_value=10000, value=100000, step=5000)
risk_pct = st.sidebar.slider("Risk Per Trade (%)", min_value=0.5, max_value=3.0, value=1.0, step=0.25) / 100
rr_ratio = st.sidebar.slider("Risk-to-Reward Ratio (1:X)", min_value=1.5, max_value=4.0, value=2.0, step=0.5)

st.sidebar.markdown("---")
max_risk_amount = round(total_capital * risk_pct, 2)
st.sidebar.metric("🛡️ Max Risk Per Trade", f"₹{max_risk_amount}")

# 3. Indicators
def calculate_indicators(df):
    df["EMA_20"] = df["Close"].ewm(span=20, adjust=False).mean()
    df["EMA_50"] = df["Close"].ewm(span=50, adjust=False).mean()
    
    delta = df["Close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / (loss + 1e-9)
    df["RSI"] = 100 - (100 / (1 + rs))
    return df

# 4. Scanner Function with Smart Decision Logic
def run_swing_scanner():
    results = []
    with st.spinner("⚡ Scanning Nifty 50 stocks..."):
        try:
            data = yf.download(WATCHLIST, period="6mo", interval="1d", group_by="ticker", threads=True, progress=False)
        except Exception as e:
            st.error(f"Data fetch error: {e}")
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

            # Must be in overall bullish trend
            if ema20 > ema50 and rsi > 50:
                entry = round(cmp_price, 2)
                swing_low = round(float(df["Low"].tail(7).min()), 2)
                risk_per_share = entry - swing_low

                if risk_per_share > 0:
                    target = round(entry + (rr_ratio * risk_per_share), 2)
                    max_risk = total_capital * risk_pct
                    qty = int(max_risk / risk_per_share)

                    # Automated Signal Classifier
                    if rsi > 70:
                        action = "WAIT / PULLBACK"
                        badge_color = "#FFC107"
                        action_desc = "RSI Overbought (>70). Wait for small dip near 20 EMA."
                    elif (risk_per_share / entry) > 0.08:
                        action = "AVOID / HIGH SL"
                        badge_color = "#DC3545"
                        action_desc = "Stop Loss is too wide (>8%). Risk-reward is unfavorable."
                    else:
                        action = "BUY / ENTER"
                        badge_color = "#28A745"
                        action_desc = "Optimal momentum setup. Safe entry with 1:2 R:R."

                    if qty > 0:
                        results.append({
                            "Stock": ticker.replace(".NS", ""),
                            "CMP": entry,
                            "StopLoss": swing_low,
                            "Target": target,
                            "Qty": qty,
                            "Action": action,
                            "BadgeColor": badge_color,
                            "ActionDesc": action_desc,
                            "HoldingPeriod": "1 - 3 Weeks",
                            "TotalCapital": round(qty * entry, 2),
                            "RiskAmount": round(qty * risk_per_share, 2),
                            "RSI": round(rsi, 2),
                            "df": df.tail(60)
                        })
        except Exception:
            continue

    return results

# 5. Journal Operations
def save_to_journal(trade_data):
    row = pd.DataFrame([{
        "Date": datetime.date.today().strftime("%Y-%m-%d"),
        "Stock": trade_data["Stock"],
        "Signal": trade_data["Action"],
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

# 6. UI Layout
tabs = st.tabs(["🚀 Live Scanner", "📓 Trade Journal", "📚 Rules & Discipline"])

# TAB 1: Live Scanner
with tabs[0]:
    col_t1, col_t2 = st.columns([3, 1])
    with col_t1:
        st.subheader("🎯 Swing Trade Signal Scanner")
        st.caption("AI Decision Logic: Auto-evaluates BUY, WAIT, or AVOID based on RSI & Risk parameters.")
    with col_t2:
        scan_btn = st.button("🔄 Scan Market Now", type="primary", use_container_width=True)

    if scan_btn or "scanned_trades" in st.session_state:
        if scan_btn:
            st.session_state.scanned_trades = run_swing_scanner()
        
        trades = st.session_state.get("scanned_trades", [])
        
        if trades:
            st.success(f"✨ Total {len(trades)} Setups Analyzed!")
            
            for idx, trade in enumerate(trades):
                with st.container():
                    # Header with Signal Badge
                    st.markdown(
                        f"### 📌 **{trade['Stock']}** &nbsp; "
                        f"<span style='background-color:{trade['BadgeColor']};color:white;padding:3px 10px;border-radius:6px;font-size:0.9rem;font-weight:bold;'>{trade['Action']}</span> "
                        f"&nbsp; `RSI: {trade['RSI']}`",
                        unsafe_allow_html=True
                    )
                    st.caption(f"💡 **AI Guidance:** {trade['ActionDesc']}")
                    
                    # Metrics Grid
                    m1, m2, m3, m4, m5 = st.columns(5)
                    m1.markdown(f"**CMP / Entry**<br><span style='font-size:1.25rem;font-weight:bold;color:#007BFF;'>₹{trade['CMP']}</span>", unsafe_allow_html=True)
                    m2.markdown(f"**Stop Loss**<br><span style='font-size:1.25rem;font-weight:bold;color:#DC3545;'>₹{trade['StopLoss']}</span>", unsafe_allow_html=True)
                    m3.markdown(f"**Target (1:{rr_ratio})**<br><span style='font-size:1.25rem;font-weight:bold;color:#28A745;'>₹{trade['Target']}</span>", unsafe_allow_html=True)
                    m4.markdown(f"**Safe Qty**<br><span style='font-size:1.25rem;font-weight:bold;'>{trade['Qty']} Shares</span>", unsafe_allow_html=True)
                    m5.markdown(f"**Holding**<br><span style='font-size:1.1rem;'>{trade['HoldingPeriod']}</span>", unsafe_allow_html=True)
                    
                    st.write("")
                    
                    # Action Buttons
                    b_col1, b_col2, b_col3 = st.columns([1, 1, 1])
                    
                    with b_col1:
                        single_msg = (
                            f"🚀 *Swing Trade Alert: {trade['Stock']}*\n"
                            f"🚦 *Signal:* {trade['Action']}\n\n"
                            f"• *CMP / Entry:* ₹{trade['CMP']}\n"
                            f"• *Stop Loss:* ₹{trade['StopLoss']}\n"
                            f"• *Target (1:{rr_ratio}):* ₹{trade['Target']}\n"
                            f"• *Safe Qty:* {trade['Qty']} shares\n"
                            f"• *Holding:* {trade['HoldingPeriod']}\n"
                            f"• *Note:* {trade['ActionDesc']}\n\n"
                            f"⚠️ _Trade with risk discipline!_"
                        )
                        wa_url = f"https://api.whatsapp.com/send?text={urllib.parse.quote(single_msg)}"
                        st.markdown(
                            f'<a href="{wa_url}" target="_blank">'
                            f'<button style="background-color:#25D366;color:white;width:100%;padding:8px;border:none;border-radius:6px;cursor:pointer;font-weight:bold;">📲 WhatsApp Alert</button>'
                            f'</a>',
                            unsafe_allow_html=True
                        )
                        
                    with b_col2:
                        if st.button(f"➕ Add to Journal", key=f"j_{idx}", use_container_width=True):
                            save_to_journal(trade)
                            st.toast(f"✅ {trade['Stock']} saved to Journal!")

                    with b_col3:
                        tv_link = f"https://in.tradingview.com/chart/?symbol=NSE:{trade['Stock']}"
                        st.markdown(
                            f'<a href="{tv_link}" target="_blank">'
                            f'<button style="background-color:#1E53E5;color:white;width:100%;padding:8px;border:none;border-radius:6px;cursor:pointer;font-weight:bold;">📈 Open TradingView</button>'
                            f'</a>',
                            unsafe_allow_html=True
                        )

                    # In-App Trend Chart
                    with st.expander(f"📊 Technical Trend Chart ({trade['Stock']})"):
                        chart_df = trade["df"]
                        fig, ax = plt.subplots(figsize=(10, 4))
                        ax.plot(chart_df.index, chart_df["Close"], label="Close Price", color="#1f77b4", linewidth=1.8)
                        ax.plot(chart_df.index, chart_df["EMA_20"], label="20 EMA", color="#2ca02c", linestyle="--", linewidth=1.5)
                        ax.plot(chart_df.index, chart_df["EMA_50"], label="50 EMA", color="#d62728", linestyle="--", linewidth=1.5)
                        ax.axhline(trade["StopLoss"], color="red", linestyle=":", label=f"SL (₹{trade['StopLoss']})")
                        ax.set_title(f"{trade['Stock']} - Price & EMA Trend", fontsize=12, fontweight='bold')
                        ax.legend(loc="upper left")
                        ax.grid(True, alpha=0.3)
                        st.pyplot(fig)
                        plt.close(fig)
                        
                    st.divider()
        else:
            st.info("Market scan complete. Koi matching setup nahi mila.")

# TAB 2: Trade Journal
with tabs[1]:
    st.subheader("📓 Trade Management Journal")
    st.caption("Track executed trades & log performance.")
    
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
        st.info("Journal abhi empty hai. Scanner se trades add karein.")

# TAB 3: Strategy Rules
with tabs[2]:
    st.subheader("📚 Pro Swing Trading Rules")
    st.markdown("""
    * 🟢 **BUY Signal:** RSI 55-70 ke beech ho aur SL reasonable ho (<8%).
    * 🟡 **WAIT / PULLBACK:** RSI > 70 par breakout chase na karein, pullback ka wait karein.
    * 🔴 **AVOID:** Agar Stop Loss 8% se bada ho, toh risk-reward align nahi hota.
    """)
