from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
import psycopg2
from kafka import KafkaProducer
import json
import os
import time
import structlog
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

# Initialize FastAPI
app = FastAPI()

# CockroachDB Connection
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://your_user:your_password@cockroachdb-service:26257/your_database")

# Kafka Configuration
KAFKA_TOPIC = "function-preparation"
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka-service:9092")
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

# JSON Logger (Loki Compatible)
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)
logger = structlog.get_logger()


# Pydantic Schema for Request Data
class FunctionPayload(BaseModel):
    name: str
    code: str
    requirements: str


@app.middleware("http")
async def log_requests(request: Request, call_next):
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


@app.post("/register/")
def register_function(payload: FunctionPayload):
    """Register a function and store it in CockroachDB."""
    logger.info("Registering function", function_name=payload.name)

    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM functions WHERE name = %s", (payload.name,))
        if cur.fetchone()[0] > 0:
            cur.close()
            conn.close()
            logger.warning("Function name already exists", function_name=payload.name)
            raise HTTPException(status_code=400, detail="Function name already exists.")
    except Exception as e:
        DB_ERRORS.inc()
        logger.error("Database error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    try:
        cur.execute("""
            INSERT INTO functions (name, state, code, requirements)
            VALUES (%s, %s, %s, %s) RETURNING id
        """, (payload.name, "registered", payload.code, payload.requirements))
        function_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        logger.info("Function registered successfully", function_id=function_id)
    except Exception as e:
        DB_ERRORS.inc()
        logger.error("Database error during insertion", error=str(e))
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    try:
        producer.send(KAFKA_TOPIC, {"id": function_id})
        logger.info("Message sent to Kafka", topic=KAFKA_TOPIC, function_id=function_id)
    except Exception as e:
        logger.error("Kafka error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Kafka unavailable. Error: {str(e)}")

    return {"id": function_id, "message": "Function registered and queued successfully."}


@app.get("/function/{function_id}")
def get_function(function_id: str):
    """Retrieve function details from CockroachDB."""
    logger.info("Fetching function details", function_id=function_id)

    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT name, code, requirements FROM functions WHERE id = %s", (function_id,))
        result = cur.fetchone()
        cur.close()
        conn.close()

        if not result:
            logger.warning("Function not found", function_id=function_id)
            raise HTTPException(status_code=404, detail="Function not found.")

        function_name, function_code, function_requirements = result
        return {
            "function_name": function_name,
            "code": function_code,
            "requirements": function_requirements
        }
    except Exception as e:
        DB_ERRORS.inc()
        logger.error("Database error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.get("/")
def health_check():
    """Health check endpoint."""
    return {"status": "Function Registration Service is running"}


@app.get("/metrics")
def metrics():
    """Expose Prometheus metrics endpoint."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
