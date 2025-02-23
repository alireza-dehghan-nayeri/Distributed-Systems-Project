import json
import os
import psycopg2
import importlib.util
from kafka import KafkaConsumer

# CockroachDB Connection
DATABASE_URL = "postgresql://your_user:your_password@cockroachdb-service:26257/your_database"

# Kafka Configuration
KAFKA_BROKER = "kafka-service:9092"
KAFKA_TOPIC = "function-execution"
FUNCTION_ID = os.getenv("FUNCTION_ID")

# Initialize Kafka Consumer
consumer = KafkaConsumer(
    KAFKA_TOPIC,
    bootstrap_servers=KAFKA_BROKER,
    value_deserializer=lambda x: json.loads(x.decode("utf-8"))
)


def get_db():
    """Get a synchronous database connection."""
    return psycopg2.connect(DATABASE_URL)


def fetch_function_code():
    """Fetch function code and dependencies from CockroachDB synchronously."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT code, requirements FROM functions WHERE id = %s", (FUNCTION_ID,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()

    if result:
        return result[0], result[1]  # function_code, function_requirements
    return None, None


def execute_function():
    """Fetch function code and execute it dynamically."""
    function_code, function_requirements = fetch_function_code()

    if not function_code:
        print("Error: Function code not found in database!")
        return

    function_file = "/app/handler.py"
    with open(function_file, "w") as f:
        f.write(function_code)

    spec = importlib.util.spec_from_file_location("handler", function_file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    if hasattr(module, "handler"):
        print("Executing handler()...")
        module.handler()
    else:
        print("Error: handler() function not found!")


def kafka_listener():
    """Listen to Kafka and process functions."""
    print("Function Preparation Service is running...")
    for msg in consumer:
        if msg.value["id"] == FUNCTION_ID:
            execute_function()
            print(f"Received function ID from Kafka: {FUNCTION_ID}")
