import asyncpg
import asyncio
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import Dict, List

# CockroachDB Connection
DATABASE_URL = "postgresql://your_user:your_password@cockroachdb-service:26257/your_database"

app = FastAPI()

# Store active WebSocket connections
active_connections: Dict[str, List[WebSocket]] = {}

async def get_db():
    """Get an asynchronous database connection."""
    return await asyncpg.connect(DATABASE_URL)

@app.post("/changefeed")
async def receive_changefeed_update(payload: dict):
    """
    Receives updates from CockroachDB Change Feed.
    Example payload:
    {
        "key": "function_id",
        "value": {
            "state": "Running"
        }
    }
    """
    function_id = payload.get("key")
    state = payload.get("value", {}).get("state")

    if not function_id or not state:
        return {"error": "Invalid payload"}

    print(f"Function {function_id} state updated to {state}")

    # Notify all connected WebSocket clients
    if function_id in active_connections:
        for ws in active_connections[function_id]:
            await ws.send_text(json.dumps({"function_id": function_id, "state": state}))

    return {"message": "Update received"}

@app.websocket("/ws/{function_id}")
async def websocket_endpoint(websocket: WebSocket, function_id: str):
    """WebSocket endpoint for clients to subscribe to function state updates."""
    await websocket.accept()

    if function_id not in active_connections:
        active_connections[function_id] = []

    active_connections[function_id].append(websocket)

    print(f"Client connected for function {function_id}")

    try:
        while True:
            await asyncio.sleep(5)  # Keep the connection alive
    except WebSocketDisconnect:
        print(f"Client disconnected from function {function_id}")
        active_connections[function_id].remove(websocket)
        if not active_connections[function_id]:
            del active_connections[function_id]

@app.get("/")
async def health_check():
    """Health check endpoint."""
    return {"status": "Function State Service is running"}
