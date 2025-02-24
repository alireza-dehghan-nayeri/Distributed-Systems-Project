build and push images using:

```
docker build -t username/name:latest .
docker push username/name:latest  
```

apply the deployment using:

```
kubectl apply -f name-deployment.yaml
```

apply the service using:

```
kubectl apply -f name-service.yaml
```