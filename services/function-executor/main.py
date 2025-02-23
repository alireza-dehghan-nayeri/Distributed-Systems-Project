from prometheus_client import start_http_server
from app.app import kafka_listener

if __name__ == "__main__":
    start_http_server(8000)  # Exposes /metrics at http://localhost:8000
    kafka_listener()
