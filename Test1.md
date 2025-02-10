Use kind instead of minikube.

brew install kind
brew install kubectl

run docker

kind create cluster --name task-cluster

now can use the cluster using:
kubectl cluster-info --context kind-task-cluster

the problem is this creates a cluster with a single node
so the following commands wont work

kubectl label node edge-node node-type=edge
kubectl label node cloud-node node-type=cloud

to fix this first we delete the created clusete using:
kind delete cluster --name task-cluster

after this using the following command we can create a kind cluster with 2 worker nodes and a control plane node:

cat <<EOF | kind create cluster --name task-cluster --config=-
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
  - role: control-plane
  - role: worker
  - role: worker
EOF

to verify we can use the following command:

kubectl get nodes

here is the output:

NAME                         STATUS     ROLES           AGE   VERSION
task-cluster-control-plane   NotReady   control-plane   15s   v1.32.0
task-cluster-worker          NotReady   <none>          5s    v1.32.0
task-cluster-worker2         NotReady   <none>          5s    v1.32.0

now we can label the worker nodes with the following commands:

kubectl label node task-cluster-worker node-type=edge
kubectl label node task-cluster-worker2 node-type=cloud

to verify we can use the following command:

kubectl get nodes --show-labels

now we can start by deploying Kafka in kubernetes.

first we install Kafka using Helm:

helm repo add bitnami https://charts.bitnami.com/bitnami
helm install kafka bitnami/kafka

helm was not istalled so i install helm :

brew install helm

now after installation i can add the repo and istall Kafka

helm repo add bitnami https://charts.bitnami.com/bitnami

to check if repo is added use 

helm repo list

now i can install Kafka:

helm install kafka bitnami/kafka

after installing Kafka i can use the following command to create a topic for tasks

kubectl exec -it $(kubectl get pods -l app.kubernetes.io/name=kafka -o jsonpath='{.items[0].metadata.name}') -- \
  kafka-topics.sh --create --topic task_queue --bootstrap-server kafka:9092

it raised this error:

Error while executing topic command : Timed out waiting for a node assignment. Call: createTopics
[2025-01-31 13:21:22,796] ERROR org.apache.kafka.common.errors.TimeoutException: Timed out waiting for a node assignment. Call: createTopics
 (org.apache.kafka.tools.TopicCommand)
command terminated with exit code 1

so i checked and it seems i installed Kafka KRaft somehow not the one with zookeeper!

so we uninstall kafka using helm:

helm uninstall kafka

then check if the pods are removed:

kubectl get pods

seems like the default kafka is now Kraft one with no zookeeper! so lets use that.

after isntalling again using the command provided before we check using:

kubectl get pods

which outputs:

NAME                 READY   STATUS    RESTARTS   AGE
kafka-controller-0   1/1     Running   0          54s
kafka-controller-1   1/1     Running   0          54s
kafka-controller-2   1/1     Running   0          54s

now we need to create the topic.

it failed again so i searched and found this: https://medium.com/@martin.hodges/deploying-kafka-on-a-kind-kubernetes-cluster-for-development-and-testing-purposes-ed7adefe03cb


now we do this to create the Kafka in the cluster 
