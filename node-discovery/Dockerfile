FROM python:3.9-slim

WORKDIR /app

RUN apt-get update && apt-get install -y protobuf-compiler && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY node-discovery.proto .
RUN python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. node-discovery.proto

COPY node-discovery.py .

EXPOSE 50051

CMD ["python", "discovery_server.py"]
