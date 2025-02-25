import asyncio
import json
import os
import structlog
import threading
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from kafka import KafkaConsumer
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "changefeed-functions")

app = FastAPI()

# Store active WebSocket connections
active_connections = set()

# Prometheus Metrics
WEBSOCKET_CONNECTIONS = Counter("websocket_connections_total", "Total WebSocket connections")
FUNCTION_UPDATES_RECEIVED = Counter("function_updates_received_total", "Total function updates received")
WS_MESSAGES_SENT = Counter("websocket_messages_sent_total", "Total messages sent over WebSocket")

# JSON Logger (Loki Compatible)
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)
logger = structlog.get_logger()

def kafka_consumer():
    """Blocking Kafka consumer runs in a separate thread."""
    consumer = KafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=KAFKA_BROKER,
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        auto_offset_reset="earliest",
        enable_auto_commit=True
    )

    logger.info("Kafka consumer started, listening for function updates...")

    for message in consumer:
        payload = message.value
        function_id = payload.get("after", {}).get("id")

        if not function_id:
            logger.warning("Invalid payload received from Kafka", payload=payload)
            continue

        FUNCTION_UPDATES_RECEIVED.inc()
        logger.info("Function updated via Kafka", function_id=function_id)

        message_json = json.dumps(payload)

        # Send the update to all connected WebSocket clients
        disconnected_clients = []
        for ws in active_connections:
            try:
                asyncio.run(ws.send_text(message_json))
                WS_MESSAGES_SENT.inc()
            except WebSocketDisconnect:
                disconnected_clients.append(ws)

        # Remove disconnected clients
        for ws in disconnected_clients:
            active_connections.remove(ws)

@app.on_event("startup")
async def start_kafka_consumer():
    """Run the Kafka consumer in a background thread."""
    thread = threading.Thread(target=kafka_consumer, daemon=True)
    thread.start()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for clients to subscribe to function state updates."""
    await websocket.accept()
    WEBSOCKET_CONNECTIONS.inc()
    logger.info("Client connected")

    active_connections.add(websocket)

    try:
        while True:
            await asyncio.sleep(5)  # Keep the connection alive
    except WebSocketDisconnect:
        logger.info("Client disconnected")
        active_connections.remove(websocket)

@app.get("/")
async def health_check():
    """Health check endpoint."""
    return {"status": "Function State Service is running"}

@app.get("/metrics")
async def metrics():
    """Expose Prometheus metrics endpoint."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
