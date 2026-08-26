import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import datetime
import urllib.parse

# Page configuration
st.set_page_config(page_title="Pro Swing Trader & Scanner", page_icon="📈", layout="wide")

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

# Sidebar - Risk Management
st.sidebar.header("💼 Capital & Risk Settings")
total_capital = st.sidebar.number_input("Total Trading Capital (₹)", min_value=1000, value=100000, step=5000)
risk_pct = st.sidebar.slider("Risk Per Trade (%)", min_value=0.5, max_value=3.0, value=1.0, step=0.25) / 100
rr_ratio = st.sidebar.slider("Risk-to-Reward Ratio (1:X)", min_value=1.5, max_value=4.0, value=2.0, step=0.5)

# Indicator calculation
def calculate_indicators(df):
    df["EMA_20"] = df["Close"].ewm(span=20, adjust=False).mean()
    df["EMA_50"] = df["Close"].ewm(span=50, adjust=False).mean()
    
    delta = df["Close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / (loss + 1e-9)
    df["RSI"] = 100 - (100 / (1 + rs))
    return df

# Scanner Function (Batch Mode)
def run_swing_scanner():
    results = []
    with st.spinner("Downloading Nifty 50 market data in batch..."):
        try:
            data = yf.download(WATCHLIST, period="6mo", interval="1d", group_by="ticker", threads=True, progress=False)
        except Exception as e:
            st.error(f"Error fetching data: {e}")
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

            # Swing Trend Filters: 20 EMA > 50 EMA & RSI > 55
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
                            "Stock": ticker.replace(".NS", ""),
                            "CMP (₹)": entry,
                            "Stop Loss (₹)": swing_low,
                            "Target (₹)": target,
                            "Qty": qty,
                            "Holding Period": "1 - 3 Weeks",
                            "Total Capital Needed (₹)": round(qty * entry, 2),
                            "Risk (₹)": round(qty * risk_per_share, 2),
                            "RSI": round(rsi, 2)
                        })
        except Exception:
            continue

    return results

# UI Layout
tab1, tab2, tab3 = st.tabs(["📊 Swing Scanner", "📓 Trade Journal & Backup", "📚 Learning Hub & Rules"])

with tab1:
    st.subheader("🎯 Swing Trading Setup Scanner")
    st.caption("Filters: 20 EMA > 50 EMA | RSI > 55 | Risk Management: 1% Rule")
    
    if st.button("🚀 Run Live Scan Now", type="primary"):
        scanned_trades = run_swing_scanner()
        if scanned_trades:
            st.success(f"🎉 Total {len(scanned_trades)} Setups Found!")
            
            # Individual Stock Cards with separate WhatsApp Buttons
            for trade in scanned_trades:
                with st.container():
                    st.markdown(f"### 📌 **{trade['Stock']}**")
                    c1, c2, c3, c4, c5 = st.columns(5)
                    c1.metric("CMP / Entry", f"₹{trade['CMP (₹)']}")
                    c2.metric("Stop Loss", f"₹{trade['Stop Loss (₹)']}")
                    c3.metric("Target (1:2)", f"₹{trade['Target (₹)']}")
                    c4.metric("Safe Quantity", f"{trade['Qty']} Shares")
                    c5.metric("Holding Period", trade["Holding Period"])
                    
                    # Single Stock WhatsApp Message Generator
                    single_msg = (
                        f"🚀 *Swing Trade Setup: {trade['Stock']}*\n\n"
                        f"• *CMP / Entry:* ₹{trade['CMP (₹)']}\n"
                        f"• *Stop Loss:* ₹{trade['Stop Loss (₹)']}\n"
                        f"• *Target (1:{rr_ratio}):* ₹{trade['Target (₹)']}\n"
                        f"• *Safe Qty:* {trade['Qty']} shares\n"
                        f"• *Expected Holding:* {trade['Holding Period']}\n"
                        f"• *Capital Required:* ₹{trade['Total Capital Needed (₹)']}\n"
                        f"• *Max Risk:* ₹{trade['Risk (₹)']}\n\n"
                        f"⚠️ _Maintain strict SL & trade discipline!_"
                    )
                    wa_url = f"https://api.whatsapp.com/send?text={urllib.parse.quote(single_msg)}"
                    st.markdown(
                        f'<a href="{wa_url}" target="_blank">'
                        f'<button style="background-color:#25D366;color:white;padding:6px 14px;border:none;border-radius:4px;cursor:pointer;font-weight:bold;margin-bottom:15px;">📲 Share {trade["Stock"]} on WhatsApp</button>'
                        f'</a>',
                        unsafe_allow_html=True
                    )
                    st.divider()
        else:
            st.info("Aaj koi setup match nahi hua. Market scan complete!")

with tab2:
    st.subheader("📓 Trade Journal")
    st.info("Scanner ke trades ko journal mein track karein.")

with tab3:
    st.subheader("📚 Swing Trading Rules")
    st.markdown("""
    * ⚖️ **1% Risk Rule:** Total capital ka maximum 1% per trade risk karein.
    * 🎯 **1:2 RR:** Target hamesha Stop Loss se minimum double rakhein.
    * ⏳ **Holding Period:** Swing trades ko setup develop hone ke liye 1 se 3 hafte ka samay dein.
    """)
