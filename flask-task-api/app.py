from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# PostgreSQL Database Configuration (from Kubernetes environment variables)
DB_HOST = "postgresql"
DB_NAME = "tasks_db"
DB_USER = "admin"
DB_PASS = "adminpassword"
app.config["SQLALCHEMY_DATABASE_URI"] = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# Task Model
class Task(db.Model):
    __tablename__ = 'tasks'
    task_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    state = db.Column(db.String, nullable=False, default="received")
    created_at = db.Column(db.DateTime, default=db.func.now())

# Home Route
@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "Flask API is running!"})

# Create Task
@app.route("/tasks/create", methods=["POST"])
def create_task():
    data = request.get_json()
    if "name" not in data:
        return jsonify({"error": "Task name is required"}), 400

    new_task = Task(name=data["name"], state="received")
    db.session.add(new_task)
    db.session.commit()
    
    return jsonify({"message": "Task created", "task_id": new_task.task_id}), 201

# Get Task Status
@app.route("/tasks/status/<int:task_id>", methods=["GET"])
def get_task_status(task_id):
    task = Task.query.get(task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404
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
