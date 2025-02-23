import json
import psycopg2
import yaml
from kafka import KafkaConsumer, KafkaProducer
from kubernetes import client, config

# CockroachDB Connection
DATABASE_URL = "postgresql://your_user:your_password@cockroachdb-service:26257/your_database"

# Kafka Configuration
KAFKA_BROKER = "kafka-service:9092"
KAFKA_CONSUMER_TOPIC = "function-deployment"
KAFKA_PRODUCER_TOPIC = "function-execution"

# Kubernetes Namespace
KUBE_NAMESPACE = "default"

# Initialize Kafka Consumer
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


def fetch_function_yaml(function_id):
    """Fetch function deployment YAML from CockroachDB synchronously."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT deployment_yaml FROM functions WHERE id = %s", (function_id,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result[0] if result else None


def fetch_function_state(function_id):
    """Fetch function state from CockroachDB synchronously."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT state FROM functions WHERE id = %s", (function_id,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result[0] if result else None


def update_function_state(function_id, new_state):
    """Update function state in CockroachDB synchronously."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE functions SET state = %s WHERE id = %s", (new_state, function_id))
    conn.commit()
    cursor.close()
    conn.close()


def deploy_kubernetes_deployment(yaml_content):
    """Deploy a Kubernetes Deployment using the Kubernetes API."""

    # Load Kubernetes config (detects if running inside Kubernetes)
    try:
        config.load_incluster_config()  # Use in-cluster config if running inside Kubernetes
    except config.ConfigException:
        config.load_kube_config()  # Use kubeconfig if running locally

    api = client.AppsV1Api()  # Kubernetes API for Deployments

    # Convert YAML string to a Python dictionary
    deployment_spec = yaml.safe_load(yaml_content)

    # Create the deployment in Kubernetes
    try:
        api.create_namespaced_deployment(namespace=KUBE_NAMESPACE, body=deployment_spec)
        print("Deployment successfully created.")
        return "Success", None
    except Exception as e:
        print(f"Deployment failed: {str(e)}")
        return None, str(e)


def process_function(function_id):
    """Process function by fetching YAML and deploying in Kubernetes."""

    state = fetch_function_state(function_id)

    update_function_state(function_id, "deployment-received")

    if state == "deployed":
        try:
            producer.send(KAFKA_PRODUCER_TOPIC, {"id": function_id})
        except Exception as e:
            print(f"Kafka unavailable. {str(e)}")

    elif state == "registered":

        # Fetch YAML from CockroachDB
        deployment_yaml = fetch_function_yaml(function_id)
        if not deployment_yaml:
            print(f"Deployment YAML not found for function ID {function_id}")
            update_function_state(function_id, "deployment-failed")
            return

        # Deploy Kubernetes Deployment
        stdout, stderr = deploy_kubernetes_deployment(deployment_yaml)

        if stderr:
            print(f"Deployment failed: {stderr}")
            update_function_state(function_id, "deployment-failed")
        else:
            print(f"Deployment succeeded: {stdout}")
            update_function_state(function_id, "deployed")


def kafka_listener():
    """Listen to Kafka and process functions."""
    print("Listening to Kafka for function deployments...")
    for msg in consumer:
        function_id = msg.value["id"]
        print(f"Received function ID from Kafka: {function_id}")
        process_function(function_id)
