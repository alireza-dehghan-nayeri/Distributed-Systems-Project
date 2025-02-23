import asyncpg
import asyncio
import json
import os
import structlog
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import Dict, List
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

# Environment Variables
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://your_user:your_password@cockroachdb-service:26257/your_database")

app = FastAPI()

# Store active WebSocket connections
active_connections: Dict[str, List[WebSocket]] = {}

# Prometheus Metrics
WEBSOCKET_CONNECTIONS = Counter("websocket_connections_total", "Total WebSocket connections")
DB_ERRORS = Counter("database_errors_total", "Total database errors")
STATE_UPDATES_RECEIVED = Counter("state_updates_received_total", "Total state updates received")
WS_MESSAGES_SENT = Counter("websocket_messages_sent_total", "Total messages sent over WebSocket")
DB_QUERY_TIME = Histogram("db_query_duration_seconds", "Time taken for database queries")

# JSON Logger (Loki Compatible)
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)
logger = structlog.get_logger()

async def get_db():
    """Get an asynchronous database connection."""
    try:
        return await asyncpg.connect(DATABASE_URL)
    except Exception as e:
        DB_ERRORS.inc()
        logger.error("Database connection error", error=str(e))
        return None

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
        logger.warning("Invalid payload received", payload=payload)
        return {"error": "Invalid payload"}

    STATE_UPDATES_RECEIVED.inc()
    logger.info("Function state updated", function_id=function_id, state=state)

    # Notify all connected WebSocket clients
    if function_id in active_connections:
        for ws in active_connections[function_id]:
            await ws.send_text(json.dumps({"function_id": function_id, "state": state}))
            WS_MESSAGES_SENT.inc()

    return {"message": "Update received"}

@app.websocket("/ws/{function_id}")
async def websocket_endpoint(websocket: WebSocket, function_id: str):
    """WebSocket endpoint for clients to subscribe to function state updates."""
    await websocket.accept()
    WEBSOCKET_CONNECTIONS.inc()
    logger.info("Client connected", function_id=function_id)

    if function_id not in active_connections:
        active_connections[function_id] = []

    active_connections[function_id].append(websocket)

    try:
        while True:
            await asyncio.sleep(5)  # Keep the connection alive
    except WebSocketDisconnect:
        logger.info("Client disconnected", function_id=function_id)
        active_connections[function_id].remove(websocket)
        if not active_connections[function_id]:
            del active_connections[function_id]

@app.get("/")
async def health_check():
    """Health check endpoint."""
    return {"status": "Function State Service is running"}

@app.get("/metrics")
async def metrics():
    """Expose Prometheus metrics endpoint."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
