First using kind i started the cluster with one control and 2 worker nodes.

```
kind create cluster --config task-cluster.yaml --name task-cluster
```

now i want to deploy the database, PostgreSQL.

```
helm install postgresql bitnami/postgresql \
  --set auth.username=admin \
  --set auth.password=adminpassword \
  --set auth.database=tasks_db
```

output:

```
NAME: postgresql
LAST DEPLOYED: Mon Feb 10 19:30:23 2025
NAMESPACE: default
STATUS: deployed
REVISION: 1
TEST SUITE: None
NOTES:
CHART NAME: postgresql
CHART VERSION: 16.4.5
APP VERSION: 17.2.0

Did you know there are enterprise versions of the Bitnami catalog? For enhanced secure software supply chain features, unlimited pulls from Docker, LTS support, or application customization, see Bitnami Premium or Tanzu Application Catalog. See https://www.arrow.com/globalecs/na/vendors/bitnami for more information.

** Please be patient while the chart is being deployed **

PostgreSQL can be accessed via port 5432 on the following DNS names from within your cluster:

    postgresql.default.svc.cluster.local - Read/Write connection

To get the password for "postgres" run:

    export POSTGRES_ADMIN_PASSWORD=$(kubectl get secret --namespace default postgresql -o jsonpath="{.data.postgres-password}" | base64 -d)

To get the password for "admin" run:

    export POSTGRES_PASSWORD=$(kubectl get secret --namespace default postgresql -o jsonpath="{.data.password}" | base64 -d)

To connect to your database run the following command:

    kubectl run postgresql-client --rm --tty -i --restart='Never' --namespace default --image docker.io/bitnami/postgresql:17.2.0-debian-12-r8 --env="PGPASSWORD=$POSTGRES_PASSWORD" \
      --command -- psql --host postgresql -U admin -d tasks_db -p 5432

    > NOTE: If you access the container using bash, make sure that you execute "/opt/bitnami/scripts/postgresql/entrypoint.sh /bin/bash" in order to avoid the error "psql: local user with ID 1001} does not exist"

To connect to your database from outside the cluster execute the following commands:

    kubectl port-forward --namespace default svc/postgresql 5432:5432 &
    PGPASSWORD="$POSTGRES_PASSWORD" psql --host 127.0.0.1 -U admin -d tasks_db -p 5432

WARNING: The configured password will be ignored on new installation in case when previous PostgreSQL release was deleted through the helm command. In that case, old PVC will have an old password, and setting it through helm won't take effect. Deleting persistent volumes (PVs) will solve the issue.

WARNING: There are "resources" sections in the chart not set. Using "resourcesPreset" is not recommended for production. For production installations, please set the following values according to your workload needs:
  - primary.resources
  - readReplicas.resources
+info https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/
```

```
kubectl get pods
NAME           READY   STATUS    RESTARTS   AGE
postgresql-0   1/1     Running   0          43s
```

```
kubectl get svc postgresql
NAME         TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)    AGE
postgresql   ClusterIP   10.96.209.114   <none>        5432/TCP   53s
```

```
kubectl get secret postgresql -o yaml
apiVersion: v1
data:
  password: YWRtaW5wYXNzd29yZA==
  postgres-password: V3hBRXcyYWNBeg==
kind: Secret
metadata:
  annotations:
    meta.helm.sh/release-name: postgresql
    meta.helm.sh/release-namespace: default
  creationTimestamp: "2025-02-10T17:30:23Z"
  labels:
    app.kubernetes.io/instance: postgresql
    app.kubernetes.io/managed-by: Helm
    app.kubernetes.io/name: postgresql
    app.kubernetes.io/version: 17.2.0
    helm.sh/chart: postgresql-16.4.5
  name: postgresql
  namespace: default
  resourceVersion: "3984"
  uid: 5cd14e70-fe35-4af5-a076-9f979b71d96f
type: Opaque
```

```
echo "YWRtaW5wYXNzd29yZA==" | base64 --decode
```

```
adminpassword%                                                           
```

test:

```
kubectl run postgresql-client --restart='Never' --image=bitnami/postgresql --command -- sleep infinity
```

```
kubectl exec -it postgresql-client -- psql -h postgresql -U admin -d tasks_db
```

```
SELECT version();
```

```
version                                             
-------------------------------------------------------------------------------------------------
 PostgreSQL 17.2 on aarch64-unknown-linux-gnu, compiled by gcc (Debian 12.2.0-14) 12.2.0, 64-bit
(1 row)
```

```
kubectl delete pod postgresql-client
```

```
pod "postgresql-client" deleted
```

```
kubectl run postgresql-client --rm --tty -i --restart='Never' --namespace default --image docker.io/bitnami/postgresql:17.2.0-debian-12-r8 --env="PGPASSWORD=$POSTGRES_PASSWORD" \
      --command -- psql --host postgresql -U admin -d tasks_db -p 5432
```

enter pass adminpassword

```
CREATE TABLE tasks (
    task_id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    state TEXT NOT NULL CHECK (state IN ('received', 'deployed', 'started', 'ended', 'crashed')),
    created_at TIMESTAMP DEFAULT NOW()
);
```

```
INSERT INTO tasks (name, state) VALUES ('Test Task', 'received');
```

```
\q
```

after this i wrote the app.py flask task api
tested it
created the docker file
created an image and tested it
created the deployment and service yaml
logged in to docker hub using docker login command

used this:
```
docker tag flask-task-api alirezadehghannayeri/flask-task-api:latest
```
to tag the image

used this:
```
docker push alirezadehghannayeri/flask-task-api:latest
```
to push the imgae

after this used this:
```
kubectl apply -f flask-deployment.yaml
```

tested it and it works
i used port forwarding
```
kubectl port-forward svc/flask-api 5001:5001
```

to access the node and use curl

```
curl http://localhost:5001/
```

now i update the flask app
bulild it again and push it:

```
docker build -t alirezadehghannayeri/flask-task-api:latest .
docker push alirezadehghannayeri/flask-task-api:latest
```

then used :

```
kubectl delete deployment flask-api
```

and then:

```
kubectl apply -f flask-deployment.yaml
```

now:

```
kubectl get pods
```

```
NAME                         READY   STATUS    RESTARTS   AGE
flask-api-595bf669cc-p8882   1/1     Running   0          38s
postgresql-0                 1/1     Running   0          45m
```

now this again:
```
kubectl port-forward svc/flask-api 5001:5001
```

then this:
```
curl -X POST "http://localhost:5001/tasks/create" -H "Content-Type: application/json" -d '{"name": "Test Task"}'
```
i got this:
```
{"message":"Task created","task_id":2}
```

then:
```
curl -X GET "http://localhost:5001/tasks/status/1"
```
```
{"created_at":"Mon, 10 Feb 2025 17:40:18 GMT","name":"Test Task","state":"received","task_id":1}
```
```
curl -X GET "http://localhost:5001/tasks/list"
```

```
[{"created_at":"Mon, 10 Feb 2025 17:40:18 GMT","name":"Test Task","state":"received","task_id":1},{"created_at":"Mon, 10 Feb 2025 18:16:12 GMT","name":"Test Task","state":"received","task_id":2}]
```

modifued the flask api.
```
docker build -t alirezadehghannayeri/flask-task-api:latest .
docker push alirezadehghannayeri/flask-task-api:latest
```

and also for sample-task
```
docker build -t alirezadehghannayeri/sample-task:latest .
docker push alirezadehghannayeri/sample-task:latest
```

then

```
kubectl delete deployment flask-api
```

then

```
kubectl apply -f flask-deployment.yaml
```

after this:

```
curl -X POST "http://localhost:5001/tasks/create" -H "Content-Type: application/json" -d '{"name": "Test Task"}'

```
i got this:

```
127.0.0.1 - - [11/Feb/2025 12:03:47] "GET /favicon.ico HTTP/1.1" 404 -
[2025-02-11 12:04:18,469] ERROR in app: Exception on /tasks/create [POST]
Traceback (most recent call last):
  File "/usr/local/lib/python3.9/site-packages/flask/app.py", line 1511, in wsgi_app
    response = self.full_dispatch_request()
  File "/usr/local/lib/python3.9/site-packages/flask/app.py", line 919, in full_dispatch_request
    rv = self.handle_user_exception(e)
  File "/usr/local/lib/python3.9/site-packages/flask/app.py", line 917, in full_dispatch_request
    rv = self.dispatch_request()
  File "/usr/local/lib/python3.9/site-packages/flask/app.py", line 902, in dispatch_request
    return self.ensure_sync(self.view_functions[rule.endpoint])(**view_args)  # type: ignore[no-any-return]
  File "/app/app.py", line 97, in create_task
    deploy_task(new_task.task_id)
  File "/app/app.py", line 65, in deploy_task
    k8s_client.create_namespaced_deployment(namespace="default", body=deployment)
  File "/usr/local/lib/python3.9/site-packages/kubernetes/client/api/apps_v1_api.py", line 353, in create_namespaced_deployment
    return self.create_namespaced_deployment_with_http_info(namespace, body, **kwargs)  # noqa: E501
  File "/usr/local/lib/python3.9/site-packages/kubernetes/client/api/apps_v1_api.py", line 452, in create_namespaced_deployment_with_http_info
    return self.api_client.call_api(
  File "/usr/local/lib/python3.9/site-packages/kubernetes/client/api_client.py", line 348, in call_api
    return self.__call_api(resource_path, method,
  File "/usr/local/lib/python3.9/site-packages/kubernetes/client/api_client.py", line 180, in __call_api
    response_data = self.request(
  File "/usr/local/lib/python3.9/site-packages/kubernetes/client/api_client.py", line 391, in request
    return self.rest_client.POST(url,
  File "/usr/local/lib/python3.9/site-packages/kubernetes/client/rest.py", line 279, in POST
    return self.request("POST", url,
  File "/usr/local/lib/python3.9/site-packages/kubernetes/client/rest.py", line 238, in request
    raise ApiException(http_resp=r)
kubernetes.client.exceptions.ApiException: (403)
Reason: Forbidden
HTTP response headers: HTTPHeaderDict({'Audit-Id': '812212d0-cd69-4d9a-87c0-43d4d3276156', 'Cache-Control': 'no-cache, private', 'Content-Type': 'application/json', 'X-Content-Type-Options': 'nosniff', 'X-Kubernetes-Pf-Flowschema-Uid': 'd8bce956-ac66-4c47-8a94-6d0e9672a0d4', 'X-Kubernetes-Pf-Prioritylevel-Uid': '4ac2c2e2-cf02-4479-a744-eabeedb469f2', 'Date': 'Tue, 11 Feb 2025 12:04:18 GMT', 'Content-Length': '329'})
HTTP response body: {"kind":"Status","apiVersion":"v1","metadata":{},"status":"Failure","message":"deployments.apps is forbidden: User \"system:serviceaccount:default:default\" cannot create resource \"deployments\" in API group \"apps\" in the namespace \"default\"","reason":"Forbidden","details":{"group":"apps","kind":"deployments"},"code":403}

```

this indicates the flask api app does not have the permission to deploy deployments!

so we need to give it the permission to do so i created the service-aacount.yaml, role.yaml, role-binding.yaml

and also added serviceAccountName: flask-api-sa to the flask-deployment.yaml

then apply them using;

```
kubectl apply -f service-account.yaml

```

```
kubectl apply -f role.yaml

```

```
kubectl apply -f role-binding.yaml

```

and again:

```
kubectl delete deployment flask-api
kubectl apply -f flask-deployment.yaml

```

now test it with:
```
curl -X POST "http://localhost:5001/tasks/create" -H "Content-Type: application/json" -d '{"name": "Test Task"}'

```

to see the logs i used:

```
kubectl logs -l app=flask-api --follow
```


now that using a request a deployment(task representative) is deployed on kubernetes, i want to add Grafana and Prometheus.

first i need to deploy them into the cluster using helm:

```
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

```

```
helm install prometheus prometheus-community/kube-prometheus-stack \
  --set prometheus.service.type=LoadBalancer \
  --set grafana.enabled=true \
  --set grafana.service.type=LoadBalancer \
  --set grafana.grafana.ini.server.root_url='http://localhost:3000' \
  --set grafana.grafana.ini.server.serve_from_sub_path=true
```

```
NAME: prometheus
LAST DEPLOYED: Tue Feb 11 17:30:37 2025
NAMESPACE: default
STATUS: deployed
REVISION: 1
NOTES:
kube-prometheus-stack has been installed. Check its status by running:
  kubectl --namespace default get pods -l "release=prometheus"

Get Grafana 'admin' user password by running:

  kubectl --namespace default get secrets prometheus-grafana -o jsonpath="{.data.admin-password}" | base64 -d ; echo

Access Grafana local instance:

  export POD_NAME=$(kubectl --namespace default get pod -l "app.kubernetes.io/name=grafana,app.kubernetes.io/instance=prometheus" -oname)
  kubectl --namespace default port-forward $POD_NAME 3000

Visit https://github.com/prometheus-operator/kube-prometheus for instructions on how to create & configure Alertmanager and Prometheus instances using the Operator.
```

```
kubectl port-forward svc/prometheus-kube-prometheus-prometheus 9090:9090
```
```
export POD_NAME=$(kubectl --namespace default get pod -l "app.kubernetes.io/name=grafana,app.kubernetes.io/instance=prometheus" -oname)
```

```
kubectl --namespace default port-forward $POD_NAME 3000
```

now from :
```
http://localhost:9090
http://localhost:3000
```

with:

```
Grafana Login: admin / prom-operator
```

USE FIREFOX FOR GRAFANA!!!

i can see the metrics from kubernetes in grafana and prometheus!

next step is to add metrics to the app.py

before that i want to clean everything so:

```
helm uninstall prometheus
```

```
helm uninstall postgresql
```

```
kubectl get nodes      
NAME                         STATUS   ROLES           AGE   VERSION
task-cluster-control-plane   Ready    control-plane   23h   v1.32.0
task-cluster-worker          Ready    <none>          23h   v1.32.0
task-cluster-worker2         Ready    <none>          23h   v1.32.0
```

```
kubectl get pods
No resources found in default namespace.
```

```
kubectl get deployments
No resources found in default namespace.
```

```
kind get clusters
task-cluster
```

to start:

- create the kind cluster
- install postgresql
- configure postgresql
- build and push the images
- forward ports
- run prometheus and grafana
- forward ports
- run the deployment
- test it using curls
- check grafana

--------------

## 5. TODO List:
- [x] Sample task implementation
- [x] Sample task Dockerfile
- [ ] Push the sample task Docker image to Docker Hub
- [x] `requirements.txt` for each Python service and update Dockerfile to use it
- [x] Flask API should check task execution status from Kubernetes
- [x] Add deployment logic to the Flask API using Kubernetes
- [ ] Automate updates in deployment pipeline


