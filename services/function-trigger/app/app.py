import psycopg2
from fastapi import FastAPI, HTTPException
from kafka.errors import KafkaTimeoutError
from pydantic import BaseModel
from kafka import KafkaProducer
import json

app = FastAPI()

# CockroachDB Connection
DATABASE_URL = "postgresql://your_user:your_password@cockroachdb-service:26257/your_database"

# Kafka Configuration
KAFKA_BROKER = "kafka-service:9092"
KAFKA_DEPLOYMENT_TOPIC = "function-deployment"
KAFKA_EXECUTION_TOPIC = "function-execution"

# Kafka Producer
producer = KafkaProducer(
    bootstrap_servers=KAFKA_BROKER,
    value_serializer=lambda v: json.dumps(v).encode("utf-8")
)


def get_db():
    """Get a synchronous database connection."""
    return psycopg2.connect(DATABASE_URL)


def check_function_status(function_id=None, function_name=None):
    """Check if the function exists and is deployment-ready."""
    conn = get_db()
    cur = conn.cursor()

    query = "SELECT id, name, state FROM functions WHERE id = %s OR name = %s"
    cur.execute(query, (function_id, function_name))
    result = cur.fetchone()

    cur.close()
    conn.close()

    if not result:
        raise HTTPException(status_code=404, detail="Function not found.")

    function_id, function_name, state = result

    if state not in ["deployable", "deployed"]:
        raise HTTPException(status_code=400, detail=f"Function is not in a deployable state. Current state: {state}")

    return function_id, function_name, state


def update_function_state(function_id, new_state):
    """Update the function's state in CockroachDB."""
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("UPDATE functions SET state = %s WHERE id = %s", (new_state, function_id))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


class FunctionTriggerRequest(BaseModel):
    function_id: str = None
    function_name: str = None


@app.post("/trigger/")
def trigger_function(payload: FunctionTriggerRequest):
    """Trigger function deployment if it is ready."""

    function_id, function_name, state = check_function_status(payload.function_id, payload.function_name)

    if state == "deployed":
        try:
            producer.send(KAFKA_EXECUTION_TOPIC, {"id": function_id})
        except KafkaTimeoutError as e:
            raise HTTPException(status_code=500, detail=f"Kafka error: {str(e)}")

        return {"message": "Function execution triggered successfully.", "function_id": function_id}


    if state == "deployable":
        try:
            producer.send(KAFKA_DEPLOYMENT_TOPIC, {"id": function_id})
        except KafkaTimeoutError as e:
            raise HTTPException(status_code=500, detail=f"Kafka error: {str(e)}")

        return {"message": "Function deployment/execution triggered successfully.", "function_id": function_id}




@app.get("/")
def health_check():
    """Health check endpoint."""
    return {"status": "Function Trigger Service is running"}
