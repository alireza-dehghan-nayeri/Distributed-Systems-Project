import grpc
import node_discovery_pb2
import node_discovery_pb2_grpc
from flask import Flask, request, jsonify

# python -m grpc_tools.protoc -I../node-discovery --python_out=. --grpc_python_out=. ../node-discovery/node-discovery.proto

GRPC_SERVER_ADDRESS = "localhost:50051"

app = Flask(__name__)

class Task:
    def __init__(self, duration, cpu_arch, memory, max_distance):
        self.duration = duration
        self.cpu_arch = cpu_arch
        self.memory = memory
        self.max_distance = max_distance
        
class Node:
    def __init__(self, node_id, name, location, cpu_arch, memory, state):
        self.node_id = node_id
        self.name = name
        self.location = location
        self.cpu_arch = cpu_arch
        self.memory = memory
        self.state = state

def get_task_by_id(task_list, task_id):
    
    for task in task_list:
        if task.task_id == task_id:
            return task
    return None

def select_best_node(nodes, task):
    
    matching_nodes = [
        node for node in nodes
        if node.cpu_arch == task.cpu_arch
        and node.memory >= task.memory
        and node.location <= task.max_distance
        and node.state == "up"
    ]

    if not matching_nodes:
        return None

    # Select the node with the smallest location distance (closest)
    best_node = min(matching_nodes, key=lambda node: node.location)
    
    return best_node

tasks = []

def get_registered_nodes():

    channel = grpc.insecure_channel(GRPC_SERVER_ADDRESS)
    stub = node_discovery_pb2_grpc.GetNodesStub(channel)

    request = node_discovery_pb2.GetNodesRequest()
    
    try:
        response = stub.GetNodes(request)
        return response.nodes
    except grpc.RpcError as e:
        print(f"Error: {e.code()} - {e.details()}")


# todo: change to gRPC afer gateway is up
@app.route('/submit_task', methods=['POST'])
def submit_task():
    
    try:
        data = request.get_json()

        required_fields = ["duration", "cpu_arch", "memory", "max_distance"]
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Missing required fields"}), 400

        duration = data["duration"]
        cpu_arch = data["cpu_arch"]
        memory = data["memory"]
        max_distance = data["max_distance"]
        
        # todo: save to db
        # todo: after saving get the saved task id
        # todo: return the saved task id to user
        task_id = len(tasks)
        tasks.append(Task(duration,cpu_arch,memory,max_distance))
    
        return jsonify({"message": "Task received successfully", "task_id": task_id}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    
# todo: change to gRPC afer gateway is up
@app.route('/execute_task', methods=['POST'])
def execute_task():
    
    try:    
        data = request.get_json()

        if not data:
            return jsonify({"error": "Request content type must be JSON"}), 415
        
        if 'task_id' not in data :
            return jsonify({"error": "Incomplete request - missing fields"}), 400
        
        task_id = data['task_id']
        
        task = get_task_by_id(tasks, task_id)

        nodes = get_registered_nodes()
        
        # todo: if no node found put it on a queue and when the node change assigne it
        if len(nodes) == 0:
            return jsonify({"error": "No Available Node"}), 500
        
        # todo: select a node
        
        selected_node = select_best_node(nodes, task)
        
        # todo: if no node found put it on a queue and when the node change assigne it
        if selected_node is not None:
            # todo: use kafka to send the msg notification
            print()
            return jsonify({"message": f"Task assigned successfully to node {selected_node.node_id}"}), 200
        else:
            return jsonify({"error": "No Matching Node"}), 500
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500



