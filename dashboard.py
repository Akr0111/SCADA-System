import streamlit as st
import pandas as pd
import asyncio
import websockets
import json
import requests
st.title("🏭 Industrial SCADA Control Room Simulator")
st.sidebar.header("Plant Substation Controls")

if st.sidebar.button("🚨 EMERGENCY TRIP BREAKER"):
    requests.post("http://localhost:8000/control/override?action=trip")
    st.sidebar.error("Substation Breaker Tripped!")
if st.sidebar.button("🔄 Reset Substation"):
    requests.post("http://localhost:8000/control/override?action=reset")
    st.sidebar.success("Substation Reset to Normal.")

placeholder = st.empty()
chart_placeholder = st.empty()
async def run_dashboard():
    uri = "ws://localhost:8000/ws/telemetry"
    history = []
    async with websockets.connect(uri) as websocket:
        while True:
            message = await websocket.recv()
            data = json.loads(message)
            history.append(data)
            if len(history) > 30:
                history.pop(0)
            df = pd.DataFrame(history)
            with placeholder.container():
                col1, col2, col3 = st.columns(3)
                col1.metric("Substation Voltage", f"{data['voltage']} V")
                col2.metric("Transformer Temp", f"{data['temperature']} °C")
                col3.metric("Breaker State", data['breaker'])
                if data['status'] == "WARNING":
                    st.warning("⚠️ High Temperature Warning Detected!")
                elif data['status'] == "TRIPPED":
                    st.error("🚨 Substation Offline / Breaker Open")
            with chart_placeholder.container():
               st.line_chart(df.set_index("timestamp")[["voltage", "temperature"]])
if __name__ == "__main__":
    asyncio.run(run_dashboard())

