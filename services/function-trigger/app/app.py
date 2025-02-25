import psycopg2
import os
import json
import time
import structlog
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from kafka.errors import KafkaTimeoutError
from kafka import KafkaProducer
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

# Initialize FastAPI
app = FastAPI()

# Environment Variables
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://root@cockroachdb-public:26257/kubelesspy_database")
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")
KAFKA_DEPLOYMENT_TOPIC = os.getenv("KAFKA_DEPLOYMENT_TOPIC", "function-deployment")
KAFKA_EXECUTION_TOPIC = os.getenv("KAFKA_EXECUTION_TOPIC", "function-execution")

# Initialize Kafka Producer
producer = KafkaProducer(
    bootstrap_servers=KAFKA_BROKER,
    value_serializer=lambda v: json.dumps(v).encode("utf-8")
)

def get_db():
    """Get a synchronous database connection."""
    return psycopg2.connect(DATABASE_URL)

# Prometheus Metrics
REQUEST_COUNT = Counter("http_requests_total", "Total HTTP requests", ["method", "endpoint", "http_status"])
REQUEST_LATENCY = Histogram("http_request_duration_seconds", "Request latency", ["method", "endpoint"])
DB_ERRORS = Counter("database_errors_total", "Total database errors")
KAFKA_MESSAGES_SENT = Counter("kafka_messages_sent_total", "Total Kafka messages sent")

# JSON Logger (Loki Compatible)
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)
logger = structlog.get_logger()

class FunctionTriggerRequest(BaseModel):
    function_id: str = None
    function_name: str = None

@app.middleware("http")
async def log_requests(request, call_next):
    """Middleware to log all API requests with Prometheus tracking."""
    start_time = time.time()
    response = await call_next(request)
    request_time = time.time() - start_time

    REQUEST_COUNT.labels(request.method, request.url.path, response.status_code).inc()
    REQUEST_LATENCY.labels(request.method, request.url.path).observe(request_time)

    logger.info(
        "API Request",
        method=request.method,
        endpoint=request.url.path,
        status_code=response.status_code,
        duration=request_time
    )
    return response

def check_function_status(function_id=None, function_name=None):
    """Check if the function exists and is deployment-ready."""
    logger.info("Checking function status", function_id=function_id, function_name=function_name)

    try:
        conn = get_db()
        cur = conn.cursor()
        query = "SELECT id, name, state FROM functions WHERE id = %s OR name = %s"
        cur.execute(query, (function_id, function_name))
        result = cur.fetchone()
        cur.close()
        conn.close()

        if not result:
            logger.warning("Function not found", function_id=function_id, function_name=function_name)
            raise HTTPException(status_code=404, detail="Function not found.")

        function_id, function_name, state = result

        if state not in ["deployable", "deployed"]:
            logger.warning("Function not in deployable state", function_id=function_id, current_state=state)
            raise HTTPException(status_code=400, detail=f"Function is not in a deployable state. Current state: {state}")

        logger.info("Function is ready", function_id=function_id, state=state)
        return function_id, function_name, state
    except Exception as e:
        DB_ERRORS.inc()
        logger.error("Database error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.post("/trigger/")
def trigger_function(payload: FunctionTriggerRequest):
    """Trigger function deployment if it is ready."""
    function_id, function_name, state = check_function_status(payload.function_id, payload.function_name)

    if state == "deployed":
        try:
            producer.send(KAFKA_EXECUTION_TOPIC, {"id": function_id})
            KAFKA_MESSAGES_SENT.inc()
            logger.info("Function execution triggered", function_id=function_id, topic=KAFKA_EXECUTION_TOPIC)
        except KafkaTimeoutError as e:
            logger.error("Kafka error", error=str(e))
            raise HTTPException(status_code=500, detail=f"Kafka error: {str(e)}")

        return {"message": "Function execution triggered successfully.", "function_id": function_id}

    if state == "deployable":
        try:
            producer.send(KAFKA_DEPLOYMENT_TOPIC, {"id": function_id})
            KAFKA_MESSAGES_SENT.inc()
            logger.info("Function deployment triggered", function_id=function_id, topic=KAFKA_DEPLOYMENT_TOPIC)
        except KafkaTimeoutError as e:
            logger.error("Kafka error", error=str(e))
            raise HTTPException(status_code=500, detail=f"Kafka error: {str(e)}")

        return {"message": "Function deployment/execution triggered successfully.", "function_id": function_id}

@app.get("/")
def health_check():
    """Health check endpoint."""
    return {"status": "Function Trigger Service is running"}

@app.get("/metrics")
def metrics():
    """Expose Prometheus metrics endpoint."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
