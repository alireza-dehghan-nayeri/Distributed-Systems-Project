```
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update
```

```
helm install kafka bitnami/kafka -f kafka-values.yaml
```

```
kubectl get pods
```

```
kubectl run kafka-client --restart='Never' --image docker.io/bitnami/kafka:latest --command -- sleep infinity
```
```
kubectl exec --tty -i kafka-client -- bash
```
```
kafka-console-producer.sh --broker-list kafka:9092 --topic test
```

```
kafka-console-consumer.sh --bootstrap-server kafka:9092 --topic test --from-beginning
```

```
helm uninstall kafka
```

```
kubectl delete pvc --all
```