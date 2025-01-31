import grpc
from concurrent import futures
import node_discovery_pb2
import node_discovery_pb2_grpc

GRPC_PORT = 50051

# question: does it need a seperate db or use cockroachDB
# todo: grpc server to let nodes register and save them to db and serve them to scheduler!

# question: node state should be saved in db! how? should nodes use kafka for state update and here we get it? or should nodes store in in db directly? trade off ?
# for now we use node name for node_id
class Node:
    def __init__(self, node_id, name, location, cpu_arch, memory, state):
        self.node_id = node_id
        self.name = name
        self.location = location
        self.cpu_arch = cpu_arch
        self.memory = memory
        self.state = state

registered_nodes = []

class NodeRegisterServicer(node_discovery_pb2_grpc.NodeRegisterServicer):
    def RegisterNode(self, request, context):
        try:
            if not request.name or not request.location or not request.cpu_arch or not request.memory:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("Missing Argument")
                return node_discovery_pb2.RegisterNodeResponse(message="Registration failed: Invalid input.")

            node_id = request.name
            registered_nodes.append(Node(node_id, request.name, request.location, request.cpu_arch, request.memory, "up"))

            return node_discovery_pb2.RegisterNodeResponse(node_id=node_id)
        
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Unexpected error: {str(e)}")
            return node_discovery_pb2.RegisterNodeResponse(node_id="")
        
class GetNodesServicer(node_discovery_pb2_grpc.GetNodesServicer):
    def GetNodes(self, request, context):
        try:
            nodes_list = [
                    node_discovery_pb2.Node(node_id=node.node_id, name=node.name, location=node.location, cpu_arch=node.cpu_arch, memory=node.memory, state=node.state) 
                    for node in registered_nodes
                ]
            return node_discovery_pb2.GetNodesResponse(nodes=nodes_list)
        
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Unexpected error: {str(e)}")
            return node_discovery_pb2.GetNodesResponse(nodes=[])


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    node_discovery_pb2_grpc.add_NodeRegisterServicer_to_server(NodeRegisterServicer(), server)
    node_discovery_pb2_grpc.add_GetNodesServicer_to_server(GetNodesServicer(), server)
    
    server.add_insecure_port(f"[::]:{GRPC_PORT}")
    
    print(f"Node Discovery Server started on port {GRPC_PORT}")

    try:
        server.start()
        server.wait_for_termination()
    except KeyboardInterrupt:
        print("\nShutting down the server gracefully...")
        server.stop(0)
    except Exception as e:
        print(f"Unexpected server error: {e}")
        server.stop(0)
        
if __name__ == "__main__":
    serve()
