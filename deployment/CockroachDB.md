```
helm repo add cockroachdb https://charts.cockroachdb.com/
helm repo update
```

```
helm install cockroachdb cockroachdb/cockroachdb -f cockroachdb-values.yaml
```

```
kubectl get pods
kubectl get svc
```

```
kubectl port-forward svc/cockroachdb-public 26257:26257
```

```
cockroach sql --insecure --host=localhost:26257
```

```
kubectl port-forward svc/cockroachdb-public 8080:8080
```

http://localhost:8080

```
helm uninstall cockroachdb
```

```
kubectl delete pvc --all
```