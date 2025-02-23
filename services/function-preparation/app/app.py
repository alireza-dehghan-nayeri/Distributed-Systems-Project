import json
import psycopg2
from kafka import KafkaConsumer

# Kubernetes Namespace
KUBE_NAMESPACE = "default"

# CockroachDB Connection
DATABASE_URL = "postgresql://your_user:your_password@cockroachdb-service:26257/your_database"

# Kafka Configuration
KAFKA_BROKER = "kafka-service:9092"
KAFKA_TOPIC = "function-preparation"

# Initialize Kafka Consumer
consumer = KafkaConsumer(
    KAFKA_TOPIC,
    bootstrap_servers=KAFKA_BROKER,
    value_deserializer=lambda x: json.loads(x.decode("utf-8"))
)


def get_db():
    """Get a synchronous database connection."""
    return psycopg2.connect(DATABASE_URL)


def generate_kubernetes_deployment_yaml(function_id):
    """Generate Kubernetes Deployment YAML that passes function_id as an environment variable."""
    deployment_name = f"func-deployment-{function_id[:8]}"

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
          restartPolicy: Always
    """

    return deployment_yaml


def process_function(function_id):
    """Process function by creating the Kubernetes job."""

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
    except Exception as e:
        print(f"Error inserting YAML into DB: {str(e)}")

    print(f"Successfully prepared function: {function_id}")


def kafka_listener():
    """Listen to Kafka and process functions."""
    print("Function Preparation Service is running...")
    for msg in consumer:
        function_id = msg.value["id"]
        print(f"Received function ID from Kafka: {function_id}")
        process_function(function_id)
