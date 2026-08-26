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
    page_title="SwingPro | AI Swing Terminal",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

JOURNAL_FILE = "trade_journal.csv"

# Custom CSS for Sleek Professional UI
st.markdown("""
<style>
    html, body, [class*="css"] {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    .metric-title {
        font-size: 0.75rem;
        color: #6c757d;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        font-weight: 600;
        margin-bottom: 2px;
    }
    .metric-val {
        font-size: 1.05rem;
        font-weight: 700;
        color: #1a1a1a;
    }
    .val-entry { color: #0969da; }
    .val-sl { color: #cf222e; }
    .val-target { color: #1a7f37; }
    
    .badge-buy {
        background-color: #dafbe1;
        color: #1a7f37;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 700;
        border: 1px solid #aceebb;
    }
    .badge-wait {
        background-color: #fff8c5;
        color: #9a6700;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 700;
        border: 1px solid #fae17d;
    }
    .badge-avoid {
        background-color: #ffebe9;
        color: #cf222e;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 700;
        border: 1px solid #ffcecb;
    }
    .stock-title {
        font-size: 1.15rem;
        font-weight: 700;
        color: #0f1419;
    }
    .advice-text {
        font-size: 0.82rem;
        color: #57606a;
        margin-top: 4px;
        margin-bottom: 8px;
    }
</style>
""", unsafe_allow_html=True)

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

# 2. Sidebar - Portfolio & Risk Settings
st.sidebar.markdown("#### 💼 Portfolio & Risk Engine")
total_capital = st.sidebar.number_input("Total Capital (₹)", min_value=10000, value=100000, step=5000)
risk_pct = st.sidebar.slider("Risk Per Trade (%)", min_value=0.5, max_value=3.0, value=1.0, step=0.25) / 100
rr_ratio = st.sidebar.slider("Risk-Reward Ratio (1:X)", min_value=1.5, max_value=4.0, value=2.0, step=0.5)

st.sidebar.markdown("---")
max_risk_amount = round(total_capital * risk_pct, 2)
st.sidebar.metric("🛡️ Max Risk Per Trade", f"₹{max_risk_amount:,.0f}")
st.sidebar.caption("Position sizing automatically keeps capital drawdowns contained.")

# 3. Indicator Calculation
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
    with st.spinner("⚡ Fetching market data & running setup algorithms..."):
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

            # Setup criteria: EMA Trend & RSI momentum
            if ema20 > ema50 and rsi > 50:
                entry = round(cmp_price, 2)
                swing_low = round(float(df["Low"].tail(7).min()), 2)
                risk_per_share = entry - swing_low

                if risk_per_share > 0:
                    target = round(entry + (rr_ratio * risk_per_share), 2)
                    max_risk = total_capital * risk_pct
                    qty = int(max_risk / risk_per_share)

                    if rsi > 70:
                        action = "WAIT / PULLBACK"
                        badge_class = "badge-wait"
                        action_desc = "RSI Overbought (>70). Wait for small pullback near 20 EMA."
                    elif (risk_per_share / entry) > 0.08:
                        action = "AVOID / WIDE SL"
                        badge_class = "badge-avoid"
                        action_desc = "Stop Loss is too wide (>8%). Risk-reward is unfavorable."
                    else:
                        action = "BUY / ENTER"
                        badge_class = "badge-buy"
                        action_desc = "Clean trend momentum. Optimal 1:2 risk-reward entry zone."

                    if qty > 0:
                        results.append({
                            "Stock": ticker.replace(".NS", ""),
                            "CMP": entry,
                            "StopLoss": swing_low,
                            "Target": target,
                            "Qty": qty,
                            "Action": action,
                            "BadgeClass": badge_class,
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
        "Stock": trade_data.get("Stock", "NA"),
        "Signal": trade_data.get("Action", "BUY"),
        "Entry_CMP": trade_data.get("CMP", 0),
        "Stop_Loss": trade_data.get("StopLoss", 0),
        "Target": trade_data.get("Target", 0),
        "Qty": trade_data.get("Qty", 0),
        "Capital_Allocated": trade_data.get("TotalCapital", 0),
        "Status": "OPEN"
    }])
    if not os.path.exists(JOURNAL_FILE):
        row.to_csv(JOURNAL_FILE, index=False)
    else:
        row.to_csv(JOURNAL_FILE, mode='a', header=False, index=False)

# 6. Main Navigation Tabs
tabs = st.tabs(["🚀 Live Scanner", "📓 Trade Journal", "📚 Strategy Rules"])

# TAB 1: Live Scanner
with tabs[0]:
    t_col1, t_col2 = st.columns([3, 1])
    with t_col1:
        st.subheader("🎯 Swing Trade Signal Scanner")
        st.caption("Filters: 20 EMA > 50 EMA | RSI > 50 | 1% Risk Allocation per Trade")
    with t_col2:
        scan_btn = st.button("🔄 Scan Market", type="primary", use_container_width=True)

    if scan_btn:
        st.session_state.scanned_trades = run_swing_scanner()
        
    trades = st.session_state.get("scanned_trades", [])
    
    if trades:
        st.success(f"⚡ {len(trades)} Setups Detected")
        
        for idx, trade in enumerate(trades):
            action_label = trade.get("Action", "BUY / ENTER")
            badge_cls = trade.get("BadgeClass", "badge-buy")
            desc = trade.get("ActionDesc", "Optimal setup")
            rsi_val = trade.get("RSI", 0)
            stock_name = trade.get("Stock", "")
            
            # Stock Header & Badge
            st.markdown(f"""
            <div style="display:flex; justify-content:space-between; align-items:center; margin-top:10px; margin-bottom: 2px;">
                <span class="stock-title">📌 {stock_name}</span>
                <span>
                    <span class="{badge_cls}">{action_label}</span>
                    <span style="font-size:0.8rem; color:#57606a; margin-left:8px; font-weight:600;">RSI: {rsi_val}</span>
                </span>
            </div>
            <div class="advice-text">💡 <b>AI Signal Note:</b> {desc}</div>
            """, unsafe_allow_html=True)

            # Metric Columns
            m1, m2, m3, m4, m5 = st.columns(5)
            m1.markdown(f"<div class='metric-title'>CMP / Entry</div><div class='metric-val val-entry'>₹{trade.get('CMP', 0)}</div>", unsafe_allow_html=True)
            m2.markdown(f"<div class='metric-title'>Stop Loss</div><div class='metric-val val-sl'>₹{trade.get('StopLoss', 0)}</div>", unsafe_allow_html=True)
            m3.markdown(f"<div class='metric-title'>Target (1:{rr_ratio})</div><div class='metric-val val-target'>₹{trade.get('Target', 0)}</div>", unsafe_allow_html=True)
            m4.markdown(f"<div class='metric-title'>Safe Qty</div><div class='metric-val'>{trade.get('Qty', 0)} Qty</div>", unsafe_allow_html=True)
            m5.markdown(f"<div class='metric-title'>Holding</div><div class='metric-val' style='font-size:0.95rem;'>{trade.get('HoldingPeriod', '1 - 3 W')}</div>", unsafe_allow_html=True)
            
            st.write("")
            
            # Action Buttons
            b_col1, b_col2, b_col3 = st.columns([1, 1, 1])
            
            with b_col1:
                single_msg = (
                    f"🚀 *Swing Trade Alert: {stock_name}*\n"
                    f"🚦 *Signal:* {action_label}\n\n"
                    f"• *CMP / Entry:* ₹{trade.get('CMP', 0)}\n"
                    f"• *Stop Loss:* ₹{trade.get('StopLoss', 0)}\n"
                    f"• *Target (1:{rr_ratio}):* ₹{trade.get('Target', 0)}\n"
                    f"• *Safe Qty:* {trade.get('Qty', 0)} shares\n"
                    f"• *Holding:* {trade.get('HoldingPeriod', '1 - 3 Weeks')}\n"
                    f"• *Note:* {desc}\n\n"
                    f"⚠️ _Trade with risk discipline!_"
                )
                wa_url = f"https://api.whatsapp.com/send?text={urllib.parse.quote(single_msg)}"
                st.markdown(
                    f'<a href="{wa_url}" target="_blank">'
                    f'<button style="background-color:#25D366;color:white;width:100%;padding:7px;border:none;border-radius:6px;cursor:pointer;font-weight:600;font-size:0.85rem;">📲 WhatsApp Alert</button>'
                    f'</a>',
                    unsafe_allow_html=True
                )
                
            with b_col2:
                if st.button("➕ Add to Journal", key=f"j_{idx}", use_container_width=True):
                    save_to_journal(trade)
                    st.toast(f"✅ {stock_name} saved to Journal!")

            with b_col3:
                tv_link = f"https://in.tradingview.com/chart/?symbol=NSE:{stock_name}"
                st.markdown(
                    f'<a href="{tv_link}" target="_blank">'
                    f'<button style="background-color:#0969da;color:white;width:100%;padding:7px;border:none;border-radius:6px;cursor:pointer;font-weight:600;font-size:0.85rem;">📈 Open Chart</button>'
                    f'</a>',
                    unsafe_allow_html=True
                )

            # In-App Trend Chart
            if "df" in trade:
                with st.expander(f"📊 View Trend Chart ({stock_name})"):
                    chart_df = trade["df"]
                    fig, ax = plt.subplots(figsize=(9, 3.2))
                    ax.plot(chart_df.index, chart_df["Close"], label="Price", color="#0969da", linewidth=1.6)
                    ax.plot(chart_df.index, chart_df["EMA_20"], label="20 EMA", color="#1a7f37", linestyle="--", linewidth=1.3)
                    ax.plot(chart_df.index, chart_df["EMA_50"], label="50 EMA", color="#cf222e", linestyle="--", linewidth=1.3)
                    ax.axhline(trade["StopLoss"], color="#cf222e", linestyle=":", label=f"SL ₹{trade['StopLoss']}")
                    ax.legend(loc="upper left", fontsize=8)
                    ax.grid(True, alpha=0.25)
                    plt.tight_layout()
                    st.pyplot(fig)
                    plt.close(fig)
                
            st.markdown("<hr style='border-top: 1px solid #e6e8eb; margin: 12px 0;'>", unsafe_allow_html=True)
    elif scan_btn:
        st.info("Market scan complete. Koi matching setup nahi mila.")

# TAB 2: Trade Journal
with tabs[1]:
    st.subheader("📓 Trade Management Journal")
    st.caption("Saved swing setups aur performance tracking.")
    
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
        st.info("Journal abhi khali hai. Live Scanner se kisi bhi trade ko add karein.")

# TAB 3: Strategy Rules
with tabs[2]:
    st.subheader("📚 Pro Swing Trading Rules")
    st.markdown("""
    * 🟢 **BUY / ENTER:** 20 EMA > 50 EMA, RSI 55-70 range mein, aur Stop Loss <8%.
    * 🟡 **WAIT / PULLBACK:** RSI > 70 par breakout chase na karein, EMA pullback ka intezar karein.
    * 🔴 **AVOID / WIDE SL:** Agar Stop Loss 8% se door ho toh capital risk balance nahi banta.
    """)
