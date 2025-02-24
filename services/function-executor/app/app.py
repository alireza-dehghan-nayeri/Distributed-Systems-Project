import json
import os
import subprocess
import time
import psycopg2
import importlib.util
import structlog
from kafka import KafkaConsumer
from prometheus_client import Counter, Histogram

# Environment Variables
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://root@cockroachdb-public:26257/kubelesspy_database")
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "function-execution")
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

# Prometheus Metrics
KAFKA_MESSAGES_PROCESSED = Counter("kafka_messages_processed_total", "Total Kafka messages processed")
DB_ERRORS = Counter("database_errors_total", "Total database errors")
DEPENDENCY_INSTALL_TIME = Histogram("dependency_installation_duration_seconds", "Time taken to install dependencies")
FUNCTION_EXECUTION_TIME = Histogram("function_execution_duration_seconds", "Time taken to execute the function")

# JSON Logger (Loki Compatible)
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)
logger = structlog.get_logger()

def fetch_function_code():
    """Fetch function code and dependencies from CockroachDB synchronously."""
    logger.info("Fetching function code", function_id=FUNCTION_ID)

    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT code, requirements FROM functions WHERE id = %s", (FUNCTION_ID,))
        result = cursor.fetchone()
        cursor.close()
        conn.close()

        if result:
            logger.info("Function code retrieved", function_id=FUNCTION_ID)
            return result[0], result[1]  # function_code, function_requirements

        logger.warning("Function code not found in database", function_id=FUNCTION_ID)
        return None, None

    except Exception as e:
        DB_ERRORS.inc()
        logger.error("Database error fetching function code", function_id=FUNCTION_ID, error=str(e))
        return None, None

def install_requirements(requirements):
    """Install Python dependencies dynamically."""
    if not requirements:
        logger.info("No additional dependencies to install", function_id=FUNCTION_ID)
        return True

    requirements_file = "/app/requirements.txt"
    with open(requirements_file, "w") as f:
        f.write(requirements)

    logger.info("Installing dependencies", function_id=FUNCTION_ID)

    start_time = time.time()
    try:
        subprocess.run(["pip", "install", "-r", requirements_file], check=True)
        install_time = time.time() - start_time
        DEPENDENCY_INSTALL_TIME.observe(install_time)
        logger.info("Dependencies installed successfully", function_id=FUNCTION_ID, duration=install_time)
        return True
    except subprocess.CalledProcessError as e:
        logger.error("Error installing dependencies", function_id=FUNCTION_ID, error=str(e))
        return False

def execute_function():
    """Fetch function code, install dependencies, and execute it dynamically."""
    logger.info("Executing function", function_id=FUNCTION_ID)

    function_code, function_requirements = fetch_function_code()
    if not function_code:
        logger.error("Error: Function code not found in database!", function_id=FUNCTION_ID)
        return

    # Install dependencies first
    if not install_requirements(function_requirements):
        logger.error("Dependency installation failed. Aborting execution.", function_id=FUNCTION_ID)
        return

    # Save function code to a file
    function_file = "/app/handler.py"
    with open(function_file, "w") as f:
        f.write(function_code)

    # Load and execute the function dynamically
    spec = importlib.util.spec_from_file_location("handler", function_file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    start_time = time.time()
    if hasattr(module, "handler"):
        logger.info("Executing handler() function", function_id=FUNCTION_ID)
        module.handler()
        execution_time = time.time() - start_time
        FUNCTION_EXECUTION_TIME.observe(execution_time)
        logger.info("Function executed successfully", function_id=FUNCTION_ID, duration=execution_time)
    else:
        logger.error("Error: handler() function not found!", function_id=FUNCTION_ID)

def kafka_listener():
    """Listen to Kafka and process functions."""
    logger.info("Function Execution Service is running...")

    for msg in consumer:
        if msg.value["id"] == FUNCTION_ID:
            KAFKA_MESSAGES_PROCESSED.inc()
            logger.info("Received function ID from Kafka", function_id=FUNCTION_ID)
            execute_function()
