import asyncio
import random
import sqlite3
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

# 1. Initialize the application
app = FastAPI()

# 2. Database Setup: Creates a local file to save historical data
def init_db():
    conn = sqlite3.connect("scada_plant.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS telemetry_logs (
            timestamp TEXT,
            voltage REAL,
            temperature REAL,
            status TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# 3. Global State: Keeps track of whether the plant is running normally or tripped
system_state = {"breaker_status": "CLOSED", "voltage_multiplier": 1.0}

# 4. The Plant Simulator: Generates fake data every second
async def telemetry_generator():
    while True:
        # If the operator tripped the breaker, voltage drops to 0
        if system_state["breaker_status"] == "OPEN":
            voltage = 0.0
            temperature = 25.0
            status = "TRIPPED"
        # Otherwise, simulate normal fluctuating power and heat
        else:
            voltage = round(220.0 + random.uniform(-10.0, 10.0) * system_state["voltage_multiplier"], 2)
            temperature = round(45.0 + random.uniform(-2.0, 8.0), 2)
            status = "NORMAL" if temperature < 50.0 else "WARNING"

        data = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "voltage": voltage,
            "temperature": temperature,
            "status": status,
            "breaker": system_state["breaker_status"]
        }

        # Save this exact reading to the SQLite database
        conn = sqlite3.connect("scada_plant.db", check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO telemetry_logs VALUES (?, ?, ?, ?)", 
                       (data["timestamp"], data["voltage"], data["temperature"], data["status"]))
        conn.commit()
        conn.close()

        await asyncio.sleep(1) # Wait 1 second before generating the next reading
        yield data

# 5. The Output Pipe: Streams data to the frontend via WebSockets
@app.websocket("/ws/telemetry")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            async for data in telemetry_generator():
                await websocket.send_json(data)
    except WebSocketDisconnect:
        print("Dashboard disconnected.")

# 6. The Input Command: Listens for operator override buttons
@app.post("/control/override")
def control_override(action: str):
    if action == "trip":
        system_state["breaker_status"] = "OPEN"
    elif action == "reset":
        system_state["breaker_status"] = "CLOSED"
    return {"status": "success"}