1 master node, 2 worker nodes

things to be done:


ssh key should be generated on local machine:

```
ssh-keygen -t rsa -b 2048
```

the public key should be set.

needed rule should be set for security group to expose ports.

the instances should be created and the ubuntu should be chosen for the image.

the instances should be set to use the ssh key.

ip should be associated with the instances so it can be accessed.

then we can connect to the instance using ssh.

on the instances kubernetes and containerd should be installed.

the following should be run in the vms using ssh:

```
sudo apt update && sudo apt upgrade -y
```

Load Required Kernel Modules:

```
sudo tee /etc/modules-load.d/kubernetes.conf <<EOF
overlay
br_netfilter
EOF
```

```
sudo modprobe overlay
sudo modprobe br_netfilter
```

Enable IP Forwarding:

```
sudo tee /etc/sysctl.d/kubernetes.conf <<EOF
net.bridge.bridge-nf-call-iptables = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.ip_forward = 1
EOF
```

```
sudo sysctl --system
```

Disable Swap (Required for Kubernetes):

```
sudo swapoff -a
sudo sed -i '/ swap / s/^/#/' /etc/fstab
```

Install containerd:

```
sudo apt update
sudo apt install -y containerd
```

Configure containerd:

```
sudo mkdir -p /etc/containerd
containerd config default | sudo tee /etc/containerd/config.toml > /dev/null
```

```
sudo sed -i 's/SystemdCgroup = false/SystemdCgroup = true/' /etc/containerd/config.toml
```

```
sudo systemctl restart containerd
sudo systemctl enable containerd
```

Install Kubernetes Components:

```
curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.30/deb/Release.key | sudo gpg --dearmor -o /etc/apt/keyrings/kubernetes-archive-keyring.gpg
echo "deb [signed-by=/etc/apt/keyrings/kubernetes-archive-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.30/deb/ /" | sudo tee /etc/apt/sources.list.d/kubernetes.list
```

```
sudo apt update
sudo apt install -y kubelet kubeadm kubectl
```

```
sudo systemctl enable kubelet
```

now kubernetes, containerd is installed and configured.

now we should configure the master node and create the cluster.

Initialize the Kubernetes Cluster on the Master Node:

```
sudo kubeadm init --pod-network-cidr=10.244.0.0/16
```

```
mkdir -p $HOME/.kube
sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config
```

```
kubectl apply -f https://raw.githubusercontent.com/coreos/flannel/master/Documentation/kube-flannel.yml
```

```
sudo systemctl restart kubelet
```

```
kubectl get nodes
kubectl get pods -n kube-system
```

Join Worker Nodes to the Cluster:

```
kubeadm token create --print-join-command
```

```
kubectl get nodes
```

on the worker nodes after installing kubernetes and containerd based on the last part we do the following:

Join the Worker Node to the Cluster:

copy the output of the following command which is ran on the master node:

```
kubeadm token create --print-join-command
```

and run it in the worker node.

in the master node check it using:

```
kubectl get nodes

NAME           STATUS   ROLES           AGE   VERSION
master-node    Ready    control-plane   82m   v1.30.10
worker-node1   Ready    <none>          28m   v1.30.10
worker-node2   Ready    <none>          17s   v1.30.10
```

DONE!

now it is time to deploy the system(application) on kubernetes cluster.

first we need to install helm on the master node:

```
curl -fsSL https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
```

```
helm version
```

now we follow the instructions on the md files I created for each component.

to enable remote access to the kubernetes cluster from local machine:

use:

```
scp -i /Users/alirezadehghannayeri/Desktop/ssh/ssh-key ubuntu@128.214.255.75:~/.kube/config ~/.kube/config
```

now the config from the vm(master node) is downloaded to the local machine.
the only problem is the config contains a certificate which is generated based on the internal local ip inside the vm.
this can be bypassed using :

```
insecure-skip-tls-verify: true
```

added to the config and the:

```
certificate-authority-data: <long-base64-string>
```

removed form the config.

now the kubectl command will work for the remote cluster on vm.

we can add the cluster to Intellij kubernetes plugin to see the logs and info.





