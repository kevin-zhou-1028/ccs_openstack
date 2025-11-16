## Overview
### Follow the instruction once the cluster is created

The deployment includes:
- **NGINX Ingress Controller** - Routes external traffic to Mattermost
- **MySQL Database** - Persistent database with 10GB storage
- **Mattermost** - The collaboration platform with 10GB file storage
- **Mattermost plugin** - Platform plugin that takes 1GB

## k8s cluster troubleshoot
### Note:
The default template has some issues with pulling many required images to create system wide pods. 
Adding labels to the template result in kube_master creation failure
Therefore, we need manually patch these pods after cluster creation
Use the following command to examine, update, and patch pods after ssh in to the mater node
```bash
# Command to check pods health status
kubectl -n kube-system get pods -o wide

# Point OCCM + Keystone-Auth to Docker Hub mirrors (the registry.k8s.io tags didn’t exist)
kubectl -n kube-system set image ds/openstack-cloud-controller-manager \
  openstack-cloud-controller-manager=docker.io/k8scloudprovider/openstack-cloud-controller-manager:v1.23.1

kubectl -n kube-system set image ds/k8s-keystone-auth \
  k8s-keystone-auth=docker.io/k8scloudprovider/k8s-keystone-auth:v1.18.0

# Use the code to examine DaemonSets roll out status
kubectl -n kube-system rollout status ds/openstack-cloud-controller-manager
kubectl -n kube-system rollout status ds/k8s-keystone-auth

# Clear the 'uninitialized' taint
kubectl taint nodes --all node.cloudprovider.kubernetes.io/uninitialized- || true
```
## Manual Deployment Steps
Executue the rest of the commands as superuser via `sudo su`
### Step 1: Install NGINX Ingress Controller

```bash
# Create namespace
kubectl create namespace ingress-nginx

# Add helm repo
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx

# Update helm repo
helm repo update

# Install ingress-nginx
helm install ingress-nginx ingress-nginx/ingress-nginx \
--version 4.3.0 \
--namespace ingress-nginx \
--create-namespace \
--set controller.service.type=NodePort

# Get the worker node IP (save this for later)
kubectl get nodes -o wide

# Get nginx port mapping
kubectl get svc -n ingress-nginx

# Update the ip address in k8s-manifests/values.yaml to external IP of worker node
# and port mapped to 80 or 443. Use port mapped to 80 is TLS is not enabled.
```


### Step 2: Deploy Mattermost Teams Edition
---
#### Note: current deployment does not have dynamic volume provisioner in place. Therefore, we need to manually create persistent volume for Mattermost. 
```bash
# Pick a node to host data, run the following command to label the node, replace <NODE_NAME> with the worker node's name.
kubectl get nodes -o wide
kubectl label node <NODE_NAME> storage=mattermost --overwrite

# SSH into the worker node to manually prepare directories for matter, you can choose any folder but we picked /mnt folder because it's guranteed to be clean to write
# Do note write to /var because linux write system files to it and mattermost will refuse to bind if the directory is not empty. Manually clearing the directory won't work

ssh -i ~/.ssh/mykey core@<worker-node-ip> # <-- do this in the shell, password is 0000
sudo mkdir -p /mnt/mattermost/app /mnt/mattermost/plugins /mnt/mattermost/mysql
sudo chmod -R 0777 /mnt/mattermost

# adjust the permission and SELinux mode on folders or mattermost do not have enough permission to write to the directories
sudo chown -R 999:999 /mnt/mattermost/app
sudo chmod -R 0777 /mnt/mattermost/app
sudo chcon -Rt svirt_sandbox_file_t /mnt/mattermost/app || true
```
#### Deploy mattermost teams edition
```bash
# ssh back to ther controller node, as super user, run the following commands
# Clone the github repo to the master node
git clone https://github.com/kevin-zhou-1028/ccs_openstack.git

# Cd into manifest folder
cd ccs_openstack/k8s-manifests/

# Create namespace
kubectl create namespace mattermost

# Add Helm repository
helm repo add mattermost https://helm.mattermost.com
helm repo update

# Provision Presistent Volume for mattermost to bind
kubectl apply -f 01-mm-pv-app.yaml -n mattermost
kubectl apply -f 02-mm-pv-plugins.yaml -n mattermost
kubectl apply -f 03-mm-pv-mysql.yaml -n mattermost

# Use the following command to confirm pv is sucessfully created
kubectl get pv -n mattermost

# install team edition
helm install mattermost -n mattermost \
  -f values.yaml \
  --set image.tag=5.35.3 \
  --set mysql.mysqlUser=sampleUser \
  --set mysql.mysqlPassword=samplePassword \
  mattermost/mattermost-team-edition

# use the following command to confirm creation status
kubectl get pods -n mattermost

# get secret used by mattermost - ignore this
kubectl get secret mattermost-mattermost-team-edition-mattermost-dbsecret -n mattermost -o jsonpath='{.data.mattermost\.dbsecret}' | base64 -d; echo

# everytime you delete mattermost you must manually delete all pv to reinstall, or previously created pv will not auto re-bound to new pvc.
# commands to delete
helm uninstall mattermost -n mattermost
kubectl delete -f 01-mm-pv-app.yaml -n mattermost
kubectl delete -f 02-mm-pv-plugins.yaml -n mattermost
kubectl delete -f 03-mm-pv-mysql.yaml -n mattermost

# if redeployment failed, it's probabaly because /mnt/mattermost/app have some remaining files. For Mattermost to deploy, it must uses empty directories. SSH into the worker node to empty /mnt/mattermost/app.
```

### Step 3: Access Mattermost

```bash
# Get the access URL
kubectl get svc -n ingress-nginx ingress-nginx-controller 
# Access Mattermost at: http://mattermost.${INGRESS_IP}.nip.io"

# Check deployment status
kubectl get mattermost -n mattermost
kubectl describe mattermost -n mattermost mattermost
```

## Troubleshooting

### Check Pod Status
```bash
kubectl get pods -n mattermost
kubectl get pods -n ingress-nginx

# Commands to confirm what mattermost's persistent volume claim is requesting
kubectl -n mattermost get pvc mattermost-mattermost-team-edition -o yaml | egrep 'storage:|accessModes|storageClassName'
kubectl -n mattermost get pvc mattermost-mattermost-team-edition-plugins -o yaml | egrep 'storage:|accessModes|storageClassName'
kubectl -n mattermost get pvc mattermost-mysql -o yaml | egrep 'storage:|accessModes|storageClassName'
```


### Check Mattermost Resource
```bash
kubectl describe mattermost -n mattermost mattermost
kubectl get mattermost -n mattermost -o yaml
```

## Cleanup

To remove the entire deployment:

```bash
# Delete Mattermost
helm uninstall mattermost -n mattermost
kubectl delete namespace mattermost

# Delete NGINX Ingress
helm uninstall nginx-ingress -n ingress-nginx
kubectl delete namespace ingress-nginx
```

## Additional Resources

- [Mattermost Kubernetes Documentation](https://docs.mattermost.com/deployment-guide/server/deploy-kubernetes.html)
- [Mattermost Operator GitHub](https://github.com/mattermost/mattermost-operator)
- [NGINX Ingress Controller](https://kubernetes.github.io/ingress-nginx/)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
