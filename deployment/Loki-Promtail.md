```
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update
```

```
helm install loki grafana/loki -f loki-values.yaml
```

```
kubectl get pods
```

```
kubectl port-forward svc/loki 3100:3100
```

http://localhost:3100

```
Add Loki as a Data Source in Grafana

Open Grafana (http://localhost:3000)
Login (admin/admin)
Go to Configuration → Data Sources
Click "Add Data Source"
Select Loki
Set the URL to:
arduino
Copy
Edit
http://loki:3100
```

```
helm uninstall loki
```

---

```
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update
```

```
helm install promtail grafana/promtail -f promtail-values.yaml
```

```
kubectl get pods
```

```
kubectl logs -l app.kubernetes.io/name=promtail
```

```
helm uninstall loki
```