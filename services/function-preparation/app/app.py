import json
import psycopg2
import os
import time
import structlog
from kafka import KafkaConsumer
from prometheus_client import Counter, Histogram

# Kubernetes Namespace
KUBE_NAMESPACE = os.getenv("KUBE_NAMESPACE", "default")

# CockroachDB Connection
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://your_user:your_password@cockroachdb-service:26257/your_database")

# Kafka Configuration
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka-service:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "function-preparation")

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
FUNCTION_PROCESSING_TIME = Histogram("function_processing_duration_seconds", "Time spent processing functions")

# JSON Logger (Loki Compatible)
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)
logger = structlog.get_logger()

def generate_kubernetes_deployment_yaml(function_id):
    """Generate Kubernetes Deployment YAML that passes function_id as an environment variable."""
    deployment_name = f"executor-{function_id[:8]}"

    deployment_yaml = f"""
    apiVersion: apps/v1
    kind: Deployment
    metadata:
      name: {deployment_name}
      namespace: {KUBE_NAMESPACE}
    spec:
      replicas: 1
      selector:
        matchLabels:
          app: {deployment_name}
      template:
        metadata:
          labels:
            app: {deployment_name}
        spec:
          containers:
            - name: function-executor 
              image: alirezadehghannayeri/function-executor:latest
              env:
                - name: FUNCTION_ID
                  value: "{function_id}"
                - name: DATABASE_URL
                  value: "{DATABASE_URL}"
                - name: KAFKA_BROKER
                  value: "{KAFKA_BROKER}"
              ports:
                - containerPort: 8000
              resources:
                requests:
                  memory: "512Mi"
                  cpu: "250m"
                limits:
                  memory: "1Gi"
                  cpu: "500m"
    """

    return deployment_yaml

def process_function(function_id):
    """Process function by creating the Kubernetes job."""
    logger.info("Processing function", function_id=function_id)

    start_time = time.time()

    # Generate Kubernetes Job YAML
    job_yaml = generate_kubernetes_deployment_yaml(function_id)

    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
                UPDATE functions 
                SET deployment_yaml = %s, state = %s 
                WHERE id = %s
            """, (job_yaml, "deployable", function_id))
        conn.commit()
        cursor.close()
        conn.close()
        logger.info("Function updated in DB", function_id=function_id, state="deployable")
    except Exception as e:
        DB_ERRORS.inc()
        logger.error("Database error", error=str(e))
        return

    processing_time = time.time() - start_time
    FUNCTION_PROCESSING_TIME.observe(processing_time)

    logger.info("Function processing complete", function_id=function_id, duration=processing_time)

def kafka_listener():
    """Listen to Kafka and process functions."""
    logger.info("Function Preparation Service is running...")

    for msg in consumer:
        function_id = msg.value["id"]
        logger.info("Received function ID from Kafka", function_id=function_id)

        KAFKA_MESSAGES_PROCESSED.inc()
        process_function(function_id)
