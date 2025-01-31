import grpc
import time
import node_discovery_pb2
import node_discovery_pb2_grpc

# python -m grpc_tools.protoc -I../node-discovery --python_out=. --grpc_python_out=. ../node-discovery/node-discovery.proto

GRPC_SERVER_ADDRESS = "localhost:50051"

def register_node(name, location, cpu_arch, memory):
    """ Registers a new node with the discovery service. """
    channel = grpc.insecure_channel(GRPC_SERVER_ADDRESS)
    stub = node_discovery_pb2_grpc.NodeRegisterStub(channel)

    request = node_discovery_pb2.RegisterNodeRequest(name=name, location=location, cpu_arch=cpu_arch, memory=memory)
    
    try:
        response = stub.RegisterNode(request)
        print(f"Registered Node ID: {response.node_id}")
        return response.node_id
    except grpc.RpcError as e:
        print(f"Error: {e.code()} - {e.details()}")
        
if __name__ == "__main__":
    time.sleep(5)
    # get the node detail from env when init
    # cpu_arch: arm64 x86_64
    node_id = register_node("name",10,"x86_64",16)
    
    # listen to kafka for tasks
        
    
    