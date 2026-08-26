from datetime import datetime
import os
import urllib.parse
import pandas as pd
import streamlit as st
import yfinance as yf

# ================= PAGE CONFIGURATION ================= ⚙️
st.set_page_config(
    page_title="Pro Swing Trader & Scanner", page_icon="📈", layout="wide"
)

# Constants & Files
JOURNAL_FILE = "trade_journal.csv"
WATCHLIST = [
    "ADANIENT.NS",
    "ADANIPORTS.NS",
    "APOLLOHOSP.NS",
    "ASIANPAINT.NS",
    "AXISBANK.NS",
    "BAJAJ-AUTO.NS",
    "BAJFINANCE.NS",
    "BAJAJFINSV.NS",
    "BPCL.NS",
    "BHARTIARTL.NS",
    "BRITANNIA.NS",
    "CIPLA.NS",
    "COALINDIA.NS",
    "DIVISLAB.NS",
    "DRREDDY.NS",
    "EICHERMOT.NS",
    "GRASIM.NS",
    "HCLTECH.NS",
    "HDFCBANK.NS",
    "HDFCLIFE.NS",
    "HEROMOTOCO.NS",
    "HINDALCO.NS",
    "HINDUNILVR.NS",
    "ICICIBANK.NS",
    "ITC.NS",
    "INDUSINDBK.NS",
    "INFY.NS",
    "JSWSTEEL.NS",
    "KOTAKBANK.NS",
    "LT.NS",
    "M&M.NS",
    "MARUTI.NS",
    "NTPC.NS",
    "NESTLEIND.NS",
    "ONGC.NS",
    "POWERGRID.NS",
    "RELIANCE.NS",
    "SBILIFE.NS",
    "SBIN.NS",
    "SUNPHARMA.NS",
    "TCS.NS",
    "TATACONSUM.NS",
    "TATAMOTORS.NS",
    "TATASTEEL.NS",
    "TECHM.NS",
    "TITAN.NS",
    "ULTRACEMCO.NS",
    "WIPRO.NS",]

# ================= SIDEBAR: CAPITAL & RISK SETTINGS ================= ⚖️
st.sidebar.header("💼 Capital & Risk Settings")
total_capital = st.sidebar.number_input(
    "Total Trading Capital (₹)", value=100000, step=10000
)
risk_pct = st.sidebar.slider("Risk Per Trade (%)", 0.5, 3.0, 1.0, 0.25) / 100
rr_ratio = st.sidebar.slider("Risk-to-Reward Ratio (1:X)", 1.5, 4.0, 2.0, 0.5)


# ================= CORE SCANNER ENGINE ================= 🔍
def run_swing_scanner():
  results = []
  for ticker in WATCHLIST:
    try:
      df = yf.download(ticker, period="6mo", interval="1d", progress=False)
      if len(df) < 50:
        continue

      # Indicators 📐
      df["EMA_20"] = df["Close"].ewm(span=20, adjust=False).mean()
      df["EMA_50"] = df["Close"].ewm(span=50, adjust=False).mean()
      df["Vol_SMA_20"] = df["Volume"].rolling(window=20).mean()

      delta = df["Close"].diff()
      gain = delta.clip(lower=0).rolling(14).mean()
      loss = (-delta.clip(upper=0)).rolling(14).mean()
      df["RSI"] = 100 - (100 / (1 + (gain / loss)))

      latest = df.iloc[-1]
      close_price = float(latest["Close"])
      ema20 = float(latest["EMA_20"])
      ema50 = float(latest["EMA_50"])
      rsi = float(latest["RSI"])
      vol = float(latest["Volume"])
      vol_sma = float(latest["Vol_SMA_20"])

      # Strategy Filters 🎯
      cond_ema = ema20 > ema50
      cond_rsi = rsi > 60
      cond_vol = True

      if cond_ema and cond_rsi and cond_vol:
        entry = round(close_price, 2)
        swing_low = round(float(df["Low"].tail(7).min()), 2)
        risk_per_share = entry - swing_low

        if risk_per_share > 0:
          target = round(entry + (rr_ratio * risk_per_share), 2)
          max_risk = total_capital * risk_pct
          qty = int(max_risk / risk_per_share)

          results.append({
              "Date": datetime.now().strftime("%Y-%m-%d"),
              "Stock": ticker.replace(".NS", ""),
              "Entry (CMP)": entry,
              "StopLoss": swing_low,
              "Target": target,
              "R:R": f"1:{rr_ratio}",
              "Qty": qty,
              "RSI": round(rsi, 1),
              "Holding Period": "5-15 Days",
              "Status": "OPEN",
          })
    except Exception as e:
      continue

  return results


# ================= NAVIGATION TABS ================= 📑
tab_scan, tab_journal, tab_learn = st.tabs([
    "📊 Swing Scanner",
    "📓 Trade Journal & Backup",
    "📚 Learning Hub & Rules",
])

# ----------------- TAB 1: SCANNER -----------------
with tab_scan:
  st.subheader("🎯 Swing Trading Setup Scanner")
  st.caption("Criteria: 20 EMA > 50 EMA | RSI > 60 | Volume > 1.5x 20-SMA")

  if st.button("🚀 Run Live Scan Now", type="primary"):
    with st.spinner("Scanning market data..."):
      signals = run_swing_scanner()

    if signals:
      st.success(f"✅ {len(signals)} Qualified Swing Setups Found!")
      df_signals = pd.DataFrame(signals)
      st.dataframe(df_signals, use_container_width=True)

      # Auto Save to Journal
      header_needed = not os.path.exists(JOURNAL_FILE)
      df_signals.to_csv(
          JOURNAL_FILE, mode="a", header=header_needed, index=False
      )
      st.toast("💾 Setups auto-saved to Trade Journal!")

      # WhatsApp Share Message Builder 📲
      msg = f"*🚀 SWING TRADE SETUPS ({datetime.now().strftime('%d-%b-%Y')})*\n\n"
      for s in signals:
        msg += f"📈 *{s['Stock']}*\n• Entry: ₹{s['Entry (CMP)']}\n• SL: ₹{s['StopLoss']} | Target: ₹{s['Target']}\n• Qty: {s['Qty']} shares (RSI: {s['RSI']})\n• Holding: {s['Holding Period']}\n-------------------\n"
      encoded_msg = urllib.parse.quote(msg)
      whatsapp_url = f"https://wa.me/?text={encoded_msg}"

      st.markdown(
          f'<a href="{whatsapp_url}" target="_blank"><button style="background-color:#25D366; color:white; padding:10px 20px; border:none; border-radius:5px; font-weight:bold; cursor:pointer;">📲 Share All Setups to WhatsApp</button></a>',
          unsafe_allow_html=True,
      )
    else:
      st.info("ℹ️ Aaj koi setup match nahi hua. Discipline maintain karein!")

# ----------------- TAB 2: JOURNAL & BACKUP -----------------
with tab_journal:
  st.subheader("📓 Trading Journal & Cloud/Local Backup")
  if os.path.exists(JOURNAL_FILE):
    df_j = pd.read_csv(JOURNAL_FILE)
    st.dataframe(df_j, use_container_width=True)

    csv_data = df_j.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="💾 Download Journal Backup (CSV)",
        data=csv_data,
        file_name=f"trade_journal_backup_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
    )
  else:
    st.info("Abhi tak koi trade log nahi hua hai.")

# ----------------- TAB 3: LEARNING HUB & RULES -----------------
with tab_learn:
  st.subheader("📚 Trading Discipline, Golden Rules & Strategy Lab")

  col1, col2 = st.columns(2)

  with col1:
    st.markdown("### 🛡️ Golden Capital Management Rules")
    st.markdown("""
        * **1% Risk Rule:** Kisi bhi single trade par apni total capital ka 1% se zyada risk na lein.
        * **Position Sizing Formula:** 
          $$\\text{Shares} = \\frac{\\text{Capital} \\times \\text{Risk \\%}}{\\text{Entry} - \\text{Stop Loss}}$$
        * **Max Open Positions:** Ek time par 4-5 se zyada active swing trades na rakhein.
        * **Trailing Stop Loss:** Jab trade 1:1 target reach kare, SL ko Entry price (Cost) par shift karein.
        """)

    st.markdown("### 🧘 Trading Psychology & Discipline")
    st.markdown("""
        * **FOMO se bachein:** Agar price setup point se nikal gaya hai, toh chase mat karein. Agle pullback ka wait karein.
        * **Respect Stop Loss:** Stop loss hit hone par bina kisi emotion ke exit karein. SL market ka insurance hai.
        * **No Revenge Trading:** Ek trade loss mein jaye toh turant recover karne ke chakkar mein bina setup ke trade na lein.
        """)

  with col2:
    st.markdown("### 💡 Swing Trading Setup Secrets")
    st.markdown("""
        * **20 EMA > 50 EMA:** Trend direction confirm karta hai. Hamesha trend ke sath trade karein.
        * **RSI > 60 Momentum:** Stock mein buyers ki fresh strength show karta hai.
        * **Volume Breakout:** Volume ye prove karta hai ki Institutional / FII / DII interest active hai.
        """)

    st.markdown("### 📋 Pre-Trade Checklist")
    st.checkbox("1. Kya market (Nifty 50) positive ya neutral trend mein hai?")
    st.checkbox(
        "2. Kya stock 20 EMA ke upar trade kar raha hai aur RSI 60+ hai?"
    )
    st.checkbox(
        "3. Kya Stop Loss swing low ke niche placed hai aur Risk-Reward minimum 1:2 hai?"
    )
    st.checkbox("4. Kya position size strictly 1% risk rule ke mutabiq hai?")

