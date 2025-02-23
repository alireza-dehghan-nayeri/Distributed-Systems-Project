```
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
```

```
helm install monitoring prometheus-community/kube-prometheus-stack \
  -f grafana-prometheus-values.yaml
```

```
kubectl get pods
```

```
kubectl port-forward svc/monitoring-kube-prometheus-stack-prometheus 9090:9090
```
http://localhost:9090

```
kubectl port-forward svc/monitoring-grafana 3000:3000
```
http://localhost:3000

```
Add Prometheus as a Data Source in Grafana

Login to Grafana (http://localhost:3000)
Go to Configuration → Data Sources
Click "Add Data Source"
Select Prometheus
Set URL to: http://monitoring-kube-prometheus-stack-prometheus:9090
Click "Save & Test"
```

```
helm uninstall monitoring 
```

to collect custom metrics:

for each service use:
```
apiVersion: v1
kind: Service
metadata:
  name: my-app-service
  labels:
    app: my-app
spec:
  selector:
    app: my-app
  ports:
    - name: http-metrics  # This name must match in ServiceMonitor
      port: 8000
      targetPort: 8000
```

create a service monitor for each service my-app-servicemonitor.yaml:

```
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: my-app-monitor
spec:
  selector:
    matchLabels:
      app: my-app  # Must match the label in your Service
  endpoints:
    - port: http-metrics  # Must match the port name in your Service
      path: /metrics
      interval: 15s  # Scrape metrics every 15 seconds
```

```
kubectl apply -f my-app-servicemonitor.yaml
```

