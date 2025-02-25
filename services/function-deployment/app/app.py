import json
import os
import time
import psycopg2
import yaml
import structlog
from kafka import KafkaConsumer, KafkaProducer
from kubernetes import client, config
from prometheus_client import Counter, Histogram

# Environment Variables
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://root@cockroachdb-public:26257/kubelesspy_database")
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")
KAFKA_CONSUMER_TOPIC = os.getenv("KAFKA_CONSUMER_TOPIC", "function-deployment")
KAFKA_PRODUCER_TOPIC = os.getenv("KAFKA_PRODUCER_TOPIC", "function-execution")
KUBE_NAMESPACE = os.getenv("KUBE_NAMESPACE", "default")

# Initialize Kafka Consumer & Producer
consumer = KafkaConsumer(
    KAFKA_CONSUMER_TOPIC,
    bootstrap_servers=KAFKA_BROKER,
    value_deserializer=lambda x: json.loads(x.decode("utf-8"))
)

producer = KafkaProducer(
    bootstrap_servers=KAFKA_BROKER,
    value_serializer=lambda v: json.dumps(v).encode("utf-8")
)

def get_db():
    """Get a synchronous database connection."""
    return psycopg2.connect(DATABASE_URL)

# Prometheus Metrics
KAFKA_MESSAGES_PROCESSED = Counter("kafka_messages_processed_total", "Total Kafka messages processed")
DB_ERRORS = Counter("database_errors_total", "Total database errors")
FUNCTION_DEPLOYMENTS = Counter("function_deployments_total", "Total function deployments")
FUNCTION_PROCESSING_TIME = Histogram("function_processing_duration_seconds", "Time spent processing functions")

# JSON Logger (Loki Compatible)
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)
logger = structlog.get_logger()

def fetch_function_yaml(function_id):
    """Fetch function deployment YAML from CockroachDB synchronously."""
    logger.info("Fetching function YAML", function_id=function_id)

    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT deployment_yaml FROM functions WHERE id = %s", (function_id,))
        result = cursor.fetchone()
        cursor.close()
        conn.close()

        if not result:
            logger.warning("No deployment YAML found", function_id=function_id)
            return None

        logger.info("Fetched deployment YAML", function_id=function_id)
        return result[0]

    except Exception as e:
        DB_ERRORS.inc()
        logger.error("Database error fetching YAML", function_id=function_id, error=str(e))
        return None

def fetch_function_state(function_id):
    """Fetch function state from CockroachDB synchronously."""
    logger.info("Fetching function state", function_id=function_id)

    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT state FROM functions WHERE id = %s", (function_id,))
        result = cursor.fetchone()
        cursor.close()
        conn.close()

        if not result:
            logger.warning("Function state not found", function_id=function_id)
            return None

        logger.info("Fetched function state", function_id=function_id, state=result[0])
        return result[0]

    except Exception as e:
        DB_ERRORS.inc()
        logger.error("Database error fetching function state", function_id=function_id, error=str(e))
        return None

def update_function_state(function_id, new_state):
    """Update function state in CockroachDB synchronously."""
    logger.info("Updating function state", function_id=function_id, new_state=new_state)

    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE functions SET state = %s WHERE id = %s", (new_state, function_id))
        conn.commit()
        cursor.close()
        conn.close()
        logger.info("Function state updated", function_id=function_id, new_state=new_state)

    except Exception as e:
        DB_ERRORS.inc()
        logger.error("Database error updating function state", function_id=function_id, error=str(e))

def deploy_kubernetes_deployment(yaml_content):
    """Deploy a Kubernetes Deployment using the Kubernetes API."""
    # todo: deploy the predefined function-executor-service.yaml and function-executor-servicemonitor to enable metrics
    logger.info("Deploying function in Kubernetes")

    try:
        # Load Kubernetes config (detects if running inside Kubernetes)
        try:
            config.load_incluster_config()  # Use in-cluster config if running inside Kubernetes
        except config.ConfigException:
            config.load_kube_config()  # Use kubeconfig if running locally

        api = client.AppsV1Api()  # Kubernetes API for Deployments

        # Convert YAML string to a Python dictionary
        deployment_spec = yaml.safe_load(yaml_content)

        # Create the deployment in Kubernetes
        api.create_namespaced_deployment(namespace=KUBE_NAMESPACE, body=deployment_spec)
        logger.info("Deployment successfully created")

        return True

    except Exception as e:
        logger.error("Kubernetes deployment failed", error=str(e))
        return False

def process_function(function_id):
    """Process function by fetching YAML and deploying in Kubernetes."""
    start_time = time.time()
    logger.info("Processing function", function_id=function_id)

    state = fetch_function_state(function_id)

    if state == "deployable":
        # Fetch YAML from CockroachDB
        deployment_yaml = fetch_function_yaml(function_id)
        if not deployment_yaml:
            return

        # Deploy Kubernetes Deployment
        if deploy_kubernetes_deployment(deployment_yaml):
            FUNCTION_DEPLOYMENTS.inc()
            update_function_state(function_id, "deployment-in-progress")

            try:
                producer.send(KAFKA_PRODUCER_TOPIC, {"id": function_id})
                logger.info("Function execution triggered", function_id=function_id, topic=KAFKA_PRODUCER_TOPIC)
            except Exception as e:
                logger.error("Kafka unavailable", function_id=function_id, error=str(e))

    FUNCTION_PROCESSING_TIME.observe(time.time() - start_time)

def kafka_listener():
    """Listen to Kafka and process functions."""
    logger.info("Listening to Kafka for function deployments...")

    for msg in consumer:
        function_id = msg.value["id"]
        logger.info("Received function ID from Kafka", function_id=function_id)

        KAFKA_MESSAGES_PROCESSED.inc()
        process_function(function_id)
