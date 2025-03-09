import asyncio
import json
import os
import structlog
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from aiokafka import AIOKafkaConsumer
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "changefeed-functions")

app = FastAPI()
active_connections = set()
message_queue = asyncio.Queue(maxsize=1000)  # Prevent memory overflow

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

async def consume_kafka():
    """Async Kafka consumer that pushes messages to an asyncio.Queue."""
    consumer = AIOKafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=KAFKA_BROKER,
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        auto_offset_reset="latest",
        enable_auto_commit=True
    )

    await consumer.start()
    logger.info("Async Kafka consumer started")

    try:
        async for message in consumer:
            payload = message.value
            FUNCTION_UPDATES_RECEIVED.inc()
            await message_queue.put(payload)
    except Exception as e:
        logger.error("Kafka consumer error", error=str(e))
    finally:
        await consumer.stop()

async def process_kafka_messages():
    """Send Kafka messages to all connected WebSockets."""
    while True:
        payload = await message_queue.get()
        message_json = json.dumps(payload)

        disconnected_clients = []
        for ws in list(active_connections):
            try:
                await ws.send_text(message_json)
                WS_MESSAGES_SENT.inc()
            except WebSocketDisconnect:
                disconnected_clients.append(ws)

        for ws in disconnected_clients:
            active_connections.discard(ws)

@app.on_event("startup")
async def start_services():
    """Start Kafka consumer and WebSocket message processor."""
    asyncio.create_task(consume_kafka())  # Start async Kafka consumer
    asyncio.create_task(process_kafka_messages())  # Start WebSocket message handler

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for clients to subscribe to function updates."""
    await websocket.accept()
    WEBSOCKET_CONNECTIONS.inc()
    logger.info("Client connected")

    active_connections.add(websocket)

    try:
        while True:
            await asyncio.sleep(5)  # Keep connection alive
    except WebSocketDisconnect:
        logger.info("Client disconnected")
        active_connections.discard(websocket)

@app.get("/")
async def health_check():
    """Health check endpoint."""
    return {"status": "Function State Service is running"}

@app.get("/metrics")
async def metrics():
    """Expose Prometheus metrics endpoint."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
