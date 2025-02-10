First using kind i started the cluster with one control and 2 worker nodes.

now i want to deploy the database, PostgreSQL.

helm install postgresql bitnami/postgresql \
  --set auth.username=admin \
  --set auth.password=adminpassword \
  --set auth.database=tasks_db

output:

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


kubectl get pods
NAME           READY   STATUS    RESTARTS   AGE
postgresql-0   1/1     Running   0          43s

kubectl get svc postgresql
NAME         TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)    AGE
postgresql   ClusterIP   10.96.209.114   <none>        5432/TCP   53s

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

echo "YWRtaW5wYXNzd29yZA==" | base64 --decode

adminpassword%                                                           

test:

kubectl run postgresql-client --restart='Never' --image=bitnami/postgresql --command -- sleep infinity


kubectl exec -it postgresql-client -- psql -h postgresql -U admin -d tasks_db


SELECT version();

version                                             
-------------------------------------------------------------------------------------------------
 PostgreSQL 17.2 on aarch64-unknown-linux-gnu, compiled by gcc (Debian 12.2.0-14) 12.2.0, 64-bit
(1 row)


kubectl delete pod postgresql-client
pod "postgresql-client" deleted

kubectl run postgresql-client --rm --tty -i --restart='Never' --namespace default --image docker.io/bitnami/postgresql:17.2.0-debian-12-r8 --env="PGPASSWORD=$POSTGRES_PASSWORD" \
      --command -- psql --host postgresql -U admin -d tasks_db -p 5432

enter pass adminpassword

CREATE TABLE tasks (
    task_id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    state TEXT NOT NULL CHECK (state IN ('received', 'deployed', 'started', 'ended', 'crashed')),
    created_at TIMESTAMP DEFAULT NOW()
);

INSERT INTO tasks (name, state) VALUES ('Test Task', 'received');

\q


after this i wrote the app.py flask task api
tested it
created the docker file
created an image and tested it
created the deployment and service yaml
logged in to docker hub using docker login command

used this:
docker tag flask-task-api alirezadehghannayeri/flask-task-api:latest
to tag the image

used this:
docker push alirezadehghannayeri/flask-task-api:latest
to push the imgae

after this used this:
kubectl apply -f flask-deployment.yaml

tested it and it works
i used port forwarding
kubectl port-forward svc/flask-api 5001:5001

to access the node and use curl
curl http://localhost:5001/

now i update the flask app
bulild it again and push it:

docker build -t alirezadehghannayeri/flask-task-api:latest .
docker push alirezadehghannayeri/flask-task-api:latest

then used :
kubectl delete deployment flask-api

and then:
kubectl apply -f flask-deployment.yaml

now:

kubectl get pods
NAME                         READY   STATUS    RESTARTS   AGE
flask-api-595bf669cc-p8882   1/1     Running   0          38s
postgresql-0                 1/1     Running   0          45m

now this again:
kubectl port-forward svc/flask-api 5001:5001


then this:
curl -X POST "http://localhost:5001/tasks/create" -H "Content-Type: application/json" -d '{"name": "Test Task"}'
i got this:
{"message":"Task created","task_id":2}

then:
curl -X GET "http://localhost:5001/tasks/status/1"
{"created_at":"Mon, 10 Feb 2025 17:40:18 GMT","name":"Test Task","state":"received","task_id":1}

 curl -X GET "http://localhost:5001/tasks/list"

[{"created_at":"Mon, 10 Feb 2025 17:40:18 GMT","name":"Test Task","state":"received","task_id":1},{"created_at":"Mon, 10 Feb 2025 18:16:12 GMT","name":"Test Task","state":"received","task_id":2}]




