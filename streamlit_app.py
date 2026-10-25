"""SATGUARD educational mission-control prototype. All data is simulated."""
import math
import random
import time
from datetime import datetime, timezone

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="SATGUARD | Mission Control", page_icon="🛰️", layout="wide")
st.markdown('''<style>
.stApp {background: #080f1d; color: #e6edf8;}
[data-testid="stSidebar"] {background: #101b2d;}
h1,h2,h3 {color: #e6edf8;}
[data-testid="stMetric"] {background:#121f33; border:1px solid #263a54; border-radius:12px; padding:16px;}
.block-container {padding-top:2rem;}
</style>''', unsafe_allow_html=True)

S = st.session_state
if "history" not in S:
    S.history = []
    S.events = []
    S.tick = 0
    S.last_sample = 0.0
    S.blocked = 0
    S.safe = False
    S.last_scenario = None


def log_event(kind, message):
    S.events.insert(0, {"Time (UTC)": datetime.now(timezone.utc).strftime("%H:%M:%S"),
                        "Type": kind, "Event": message})
    S.events = S.events[:100]


with st.sidebar:
    st.title("🛰️ SATGUARD")
    st.caption("MISSION CONTROL / SATFORGE")
    running = st.toggle("Auto-update telemetry", value=True)
    interval = st.slider("Update interval (seconds)", 1, 10, 2)
    scenario = st.selectbox("Demo scenario", ["Nominal operations", "Low battery", "High temperature", "Communication loss"])
    st.divider()
    st.caption("Security demonstration")
    if st.button("Simulate unauthorized command", use_container_width=True):
        S.blocked += 1
        log_event("SECURITY", "Demo command rejected: simulated authentication failure.")
    if st.button("Simulate replayed command", use_container_width=True):
        S.blocked += 1
        log_event("SECURITY", "Demo command rejected: simulated duplicate sequence number.")
    if st.button("Toggle safe mode", use_container_width=True):
        S.safe = not S.safe
        log_event("COMMAND", "Safe mode " + ("enabled" if S.safe else "disabled") + " by demo operator.")
    if st.button("Reset demo session", use_container_width=True):
        for key in ["history", "events", "tick", "last_sample", "blocked", "safe", "last_scenario"]:
            del S[key]
        st.rerun()
    st.caption("Each viewer has an independent demo session. Logs are temporary; export before closing.")

st.title("SATGUARD Mission Control")
st.caption("Satellite health • Communications • Security monitoring")
st.info("SIMULATION MODE — All telemetry and security events are generated for demonstration. No satellite or hardware is connected.")


@st.fragment(run_every=interval if running else None)
def dashboard():
    if S.last_scenario != scenario:
        log_event("SYSTEM", "Scenario selected: " + scenario)
        S.last_scenario = scenario
        S.last_sample = 0.0
    now = time.monotonic()
    if not S.history or (running and now - S.last_sample >= interval * 0.8):
        S.tick += 1
        phase = S.tick / 15
        battery = 78 + 4 * math.sin(phase)
        temp = 26 + 2 * math.sin(phase / 2)
        rssi = -79 + random.uniform(-3, 3)
        loss = random.uniform(0, 1.5)
        if scenario == "Low battery":
            battery = 17 + random.uniform(-1, 1)
        elif scenario == "High temperature":
            temp = 64 + random.uniform(-1, 1)
        elif scenario == "Communication loss":
            rssi, loss = None, 100.0
        voltage = 3.3 + battery / 100 * 0.9
        current = (0.12 if S.safe else 0.32) + random.uniform(-0.015, 0.015)
        S.history.append({"Time (UTC)": datetime.now(timezone.utc), "Battery (%)": round(battery, 1),
                          "Temperature (°C)": round(temp, 1), "Voltage (V)": round(voltage, 2),
                          "Current (A)": round(current, 3), "RSSI (dBm)": rssi,
                          "Packet loss (%)": round(loss, 2)})
        S.history = S.history[-300:]
        S.last_sample = now
    data = pd.DataFrame(S.history)
    row = S.history[-1]
    cols = st.columns(4)
    cols[0].metric("Battery", f'{row["Battery (%)"]:.1f}%')
    cols[1].metric("Temperature", f'{row["Temperature (°C)"]:.1f} °C')
    cols[2].metric("Bus voltage", f'{row["Voltage (V)"]:.2f} V')
    cols[3].metric("Rejected demo commands", S.blocked)
    st.caption("Last sample: " + row["Time (UTC)"].strftime("%H:%M:%S UTC") + (" • Auto-update active" if running else " • Paused"))
    alerts = []
    if row["Battery (%)"] < 20:
        alerts.append("Low battery: below the demo threshold of 20%.")
    if row["Temperature (°C)"] > 60:
        alerts.append("High temperature: above the demo threshold of 60 °C.")
    if row["Packet loss (%)"] == 100:
        alerts.append("Communication loss: no simulated packets received.")
    for alert in alerts:
        st.error(alert)
    if not alerts:
        st.success("Simulated health readings within demo thresholds.")
    overview, security, telemetry = st.tabs(["Mission overview", "Security & command log", "Telemetry export"])
    with overview:
        left, right = st.columns([2, 1])
        with left:
            selected = st.selectbox("Telemetry graph", ["Battery (%)", "Temperature (°C)", "Voltage (V)", "Current (A)", "RSSI (dBm)", "Packet loss (%)"])
            fig = go.Figure(go.Scatter(x=data["Time (UTC)"], y=data[selected], mode="lines", line=dict(color="#55d8ee", width=3), connectgaps=False))
            fig.update_layout(template="plotly_dark", paper_bgcolor="#080f1d", plot_bgcolor="#101b2d", height=350,
                              margin=dict(l=20, r=20, t=20, b=20), xaxis_title="Time (UTC)", yaxis_title=selected)
            st.plotly_chart(fig, use_container_width=True)
        with right:
            st.subheader("System status")
            st.write("**Operating mode:** " + ("SAFE" if S.safe else "NOMINAL"))
            st.write("**Link:** " + ("LOST" if row["RSSI (dBm)"] is None else "CONNECTED (simulated)"))
            st.write("**RSSI:** " + ("No signal" if row["RSSI (dBm)"] is None else f'{row["RSSI (dBm)"]:.1f} dBm'))
            st.write(f'**Packet loss:** {row["Packet loss (%)"]:.2f}%')
            st.write(f'**Bus current:** {row["Current (A)"]:.3f} A')
            st.caption("Safe mode reduces simulated current draw. Thresholds and electrical values are illustrative; validate against the final hardware.")
    with security:
        st.subheader("Security demonstration")
        st.write("Use the sidebar to demonstrate rejected unauthorized or replayed commands. Each action adds a timestamped event below.")
        st.caption("These buttons simulate validation results. They do not implement cryptographic authentication, encryption, or a flight command interface.")
        st.dataframe(pd.DataFrame(S.events), hide_index=True, use_container_width=True)
        st.download_button("Download event log", pd.DataFrame(S.events).to_csv(index=False).encode(), "satguard_events.csv", "text/csv")
    with telemetry:
        st.dataframe(data.iloc[::-1], hide_index=True, use_container_width=True)
        st.download_button("Download telemetry CSV", data.to_csv(index=False).encode(), "satguard_telemetry.csv", "text/csv")
        st.caption("The latest 300 samples are retained per viewer. Downloads contain a snapshot at rendering time.")


dashboard()
