from flask import Flask, request, jsonify, Response
from flask_sqlalchemy import SQLAlchemy
from kubernetes import client, config
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST, Counter

REQUEST_COUNT = Counter('flask_request_count', 'Total number of requests')


app = Flask(__name__)

# PostgreSQL Database Configuration (from Kubernetes environment variables)
DB_HOST = "postgresql"
DB_NAME = "tasks_db"
DB_USER = "admin"
DB_PASS = "adminpassword"
app.config["SQLALCHEMY_DATABASE_URI"] = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# Load Kubernetes config inside the cluster
config.load_incluster_config()
k8s_client = client.CoreV1Api()

def get_task_status(task_id):
    """ Fetches task status from Kubernetes """
    pod_list = k8s_client.list_namespaced_pod(namespace="default", label_selector=f"task_id={task_id}")

    if not pod_list.items:
        return "ended"  # If the pod is gone, assume task is done

    pod = pod_list.items[0]
    if pod.status.phase == "Pending":
        return "deployed"
    elif pod.status.phase == "Running":
        return "started"
    elif pod.status.phase in ["Succeeded", "Failed"]:
        return "ended"  # Task finished (either successfully or crashed)
    
    return "unknown"

def deploy_task(task_id):
    """ Deploys a task as a Kubernetes Deployment """
    deployment_name = f"task-{task_id}"
    container_image = "alirezadehghannayeri/sample-task:latest"

    deployment = client.V1Deployment(
        metadata=client.V1ObjectMeta(name=deployment_name),
        spec=client.V1DeploymentSpec(
            replicas=1,
            selector={"matchLabels": {"app": deployment_name}},
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(labels={"app": deployment_name, "task_id": str(task_id)}),
                spec=client.V1PodSpec(
                    containers=[
                        client.V1Container(
                            name="sample-task",
                            image=container_image
                        )
                    ]
                )
            )
        )
    )

    # Deploy task in Kubernetes
    k8s_client = client.AppsV1Api()
    k8s_client.create_namespaced_deployment(namespace="default", body=deployment)

    # Update database state to "deployed"
    task = Task.query.get(task_id)
    task.state = "deployed"
    db.session.commit()


# Task Model
class Task(db.Model):
    __tablename__ = 'tasks'
    task_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    state = db.Column(db.String, nullable=False, default="received")
    created_at = db.Column(db.DateTime, default=db.func.now())
    
@app.before_request
def before_request():
    REQUEST_COUNT.inc()


@app.route('/metrics')
def metrics():
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

# Home Route
@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "Flask API is running!"})

@app.route("/tasks/create", methods=["POST"])
def create_task():
    data = request.get_json()
    if "name" not in data:
        return jsonify({"error": "Task name is required"}), 400

    new_task = Task(name=data["name"], state="received")
    db.session.add(new_task)
    db.session.commit()

    # Deploy task in Kubernetes
    deploy_task(new_task.task_id)

    return jsonify({"message": "Task created and deployed", "task_id": new_task.task_id}), 201

@app.route("/tasks/status/<int:task_id>", methods=["GET"])
def check_task_status(task_id):
    task = Task.query.get(task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404

    # Get Kubernetes task state
    task.state = get_task_status(task_id)
    db.session.commit()

    return jsonify({"task_id": task.task_id, "name": task.name, "state": task.state, "created_at": task.created_at})

# List All Tasks
@app.route("/tasks/list", methods=["GET"])
def list_tasks():
    tasks = Task.query.all()
    task_list = [{"task_id": task.task_id, "name": task.name, "state": task.state, "created_at": task.created_at} for task in tasks]
    return jsonify(task_list)

# Stop (Delete) a Task
@app.route("/tasks/stop/<int:task_id>", methods=["DELETE"])
def stop_task(task_id):
    task = Task.query.get(task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404

    db.session.delete(task)
    db.session.commit()
    return jsonify({"message": "Task stopped and removed"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
