from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import psycopg2
from kafka import KafkaProducer
import json

# Initialize FastAPI
app = FastAPI()

# CockroachDB Connection
DATABASE_URL = "postgresql://your_user:your_password@cockroachdb-service:26257/your_database"

# Kafka Producer Configuration
KAFKA_TOPIC = "function-preparation"
KAFKA_BROKER = "kafka-service:9092"
producer = KafkaProducer(
    bootstrap_servers=KAFKA_BROKER,
    value_serializer=lambda v: json.dumps(v).encode("utf-8")
)


def get_db():
    """Get a synchronous database connection."""
    return psycopg2.connect(DATABASE_URL)


# Pydantic Schema for Request Data
class FunctionPayload(BaseModel):
    name: str
    code: str
    requirements: str


@app.post("/register/")
def register_function(payload: FunctionPayload):
    """Register a function and store it in CockroachDB."""

    # Ensure function name is unique
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM functions WHERE name = %s", (payload.name,))
        if cur.fetchone()[0] > 0:
            cur.close()
            conn.close()
            raise HTTPException(status_code=400, detail="Function name already exists.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    # Insert function into CockroachDB
    try:
        cur.execute("""
            INSERT INTO functions (name, state, code, requirements)
            VALUES (%s, %s, %s, %s) RETURNING id
        """, (payload.name, "registration-received", payload.code, payload.requirements))
        function_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    # Publish function ID to Kafka
    try:
        producer.send(KAFKA_TOPIC, {"id": function_id})
    except Exception as e:
        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute("UPDATE functions SET state = 'registration-preparation-failed' WHERE id = %s", (function_id,))
            conn.commit()
            cur.close()
            conn.close()
        except Exception as db_error:
            raise HTTPException(status_code=500,
                                detail=f"Both Kafka and DB failed: Kafka Error: {str(e)}, DB Error: {str(db_error)}")

        raise HTTPException(status_code=500, detail=f"Kafka unavailable. Function failed. Error: {str(e)}")

    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("UPDATE functions SET state = 'registration-preparation-queued' WHERE id = %s",
                    (function_id,))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Function registered but DB update to 'queued' failed: {str(e)}")

    return {"id": function_id, "message": "Function registered an queued successfully."}


@app.get("/function/{function_id}")
def get_function(function_id: str):
    """Retrieve function details from CockroachDB."""
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT name, code, requirements FROM functions WHERE id = %s", (function_id,))
        result = cur.fetchone()
        cur.close()
        conn.close()

        if not result:
            raise HTTPException(status_code=404, detail="Function not found.")

        function_name, function_code, function_requirements = result

        return {
            "function_name": function_name,
            "code": function_code,
            "requirements": function_requirements
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.get("/")
def health_check():
    """Health check endpoint."""
    return {"status": "Function Registration Service is running"}
