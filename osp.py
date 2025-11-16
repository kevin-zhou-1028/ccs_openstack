# profile.py: A geni-lib script to deploy a multi-node
# OpenStack + Kubernetes environment on CloudLab.

"""
Multi-node OpenStack + Kubernetes deployment optimized for Mattermost on Ubuntu 24.04.
This profile provisions a production-ready OpenStack environment with:
- OpenStack core services (Nova, Neutron, Cinder, Glance, Heat, Horizon)
- Octavia Load Balancer for high availability
- Kubernetes support via OpenStack Magnum
- VM flavors optimized for Mattermost (4GB+ RAM)
- One controller node and user-defined number of compute nodes

Instructions:
## Basic Instructions

**PATIENCE IS KEY!** The OpenStack installation and configuration process is complex and can take 30-60 minutes to complete.
- While the experiment nodes are being provisioned, you can monitor the `logs` on the project page.
- When the nodes start booting, you can inspect their status either in `Topology View` or `List View`.
- Once a node is booted and it's 'Status' column shows 'ready', you can click on the settings gear icon on the right side of the experiment page to open a shell to the node.
    - You can monitor the setup progress by viewing log files or by inspecting running services.
    - Browse to `/opt/stack/logs/`. You can use `tail -f <logfile>` to monitor log files in real-time.
    - Use `$ systemctl status <service>` to check the status of services.

Once the controller node's `Status` changes to `ready`, and profile configuration scripts finish configuring OpenStack (indicated by `Startup` column changing to `Finished`), you'll be able to visit and log in to [the OpenStack Dashboard](http://{host-controller}/dashboard).
Default dashboard credentials are:
1. `admin` / `chocolateFrog!`
2. `demo` / `chocolateFrog!`

### OpenStack Login Credentials
Default: `crookshanks` / `chocolateFrog!`
If you changed the default values and forgot what you set it to, click on the `Bindings` tab on the experiment page to see the custom settings.

### Deploying Mattermost

This profile is optimized for Mattermost deployment with k8s:

#### Kubernetes Deployment
1. Deploy a Kubernetes cluster using Magnum (see instructions below)
2. Install Mattermost using Helm chart
3. Use Kubernetes LoadBalancer service type with Octavia

### Some commands to run on the controller node

Click on the settings gear icon on the right side of the experiment page to open a shell to the controller node.

#### Run every time you open a new shell
```bash
$ source /opt/devstack/openrc admin admin
```

#### Create Keypair and Deploy a Kubernetes Cluster
```bash
$ ssh-keygen -t rsa -b 4096 -f ~/.ssh/mykey
$ openstack keypair create --public-key ~/.ssh/mykey.pub mykey
$ chmod 600 ~/.ssh/mykey  # Set proper permissions for the private key
$ openstack keypair list	# To Confirm the keypair was created.

$ openstack [option] --help
$ openstack coe cluster template list # This shows a list of custom K8s templates. # Note the UUID of the required template.

$ openstack coe cluster create --cluster-template <UUID> --master-count 1 --node-count 1 --keypair mykey  mattermost-k8s-cluster	# Creates a K8s deployment named 'mattermost-k8s-cluster' with 1 worker node. Replace <UUID> with the actual UUID as noted previously.
$ watch openstack coe cluster show mattermost-k8s-cluster    # Monitor the cluster creation process.

$ openstack stack list  # Note the stack ID of the cluster.
$ watch openstack stack resource list <stack_id>  # Replace <stack_id> with the actual stack ID.

# If cluster creation is unsuccessful, note it's Stack name and resource name to see the error message:
$ openstack stack list  # Note the stack name of the failed cluster.
$ openstack stack resource list <failed-stack-name> # Replace <failed-stack-name> with the actual stack name and note the failed resource's name.
$ openstack stack resource show <failed-stack-name> <failed-resource-name>  # Replace <failed-stack-name> and <failed-resource-name> with actual values to see the error message.
```

After the cluster is successfully created, you can ssh into a node using `ssh -i ~/.ssh/mykey core@<node-ip>`. You can get the node IPs from the [dashboard](http://{host-controller}/dashboard) or by running `openstack server list`.

#### Deploy Mattermost on Kubernetes

Mattermost requires three key components:
1. **NGINX Ingress Controller** - for routing external traffic
2. **PostgreSQL Database** - for data storage with persistent volumes
3. **Persistent Storage** - for file uploads and attachments

##### Step 1: Get Kubernetes Cluster Access

##### Step 2: Install Helm (if not already installed)

##### Step 3: Install NGINX Ingress Controller

##### Step 4: Deploy PostgreSQL Database

##### Step 5: Install Mattermost Operator

##### Step 6: Create Database Connection Secret

##### Step 7: Create Mattermost Filestore PVC

##### Step 8: Deploy Mattermost

##### Step 9: Access Mattermost

#### Deployment Scripts
- `scripts/01-install-openstack.sh` - Installs and configures OpenStack
- `scripts/02-configure-magnum.sh` - Configures Magnum for Kubernetes

#### Kubernetes Manifests
The `k8s-manifests/` directory contains:
- PostgreSQL database deployment with persistent storage
- Mattermost Operator configuration
- Mattermost installation manifests
- NGINX Ingress configuration templates

### Resources
- [CloudLab Documentation](https://docs.cloudlab.us/)
- [OpenStack Documentation](https://docs.openstack.org/)
- [Mattermost Installation Guide](https://docs.mattermost.com/install/install-ubuntu.html)
- [Mattermost Kubernetes Deployment](https://docs.mattermost.com/deployment-guide/server/deploy-kubernetes.html)
- [Mattermost Operator](https://github.com/mattermost/mattermost-operator)
- [Mattermost Helm Chart](https://github.com/mattermost/mattermost-helm)
- [Kubernetes Documentation](https://kubernetes.io/docs/home/)
- [NGINX Ingress Controller](https://kubernetes.github.io/ingress-nginx/)
- [DevStack Documentation](https://docs.openstack.org/devstack/latest/)
- [Magnum Documentation](https://docs.openstack.org/magnum/latest/)
- [Octavia Documentation](https://docs.openstack.org/octavia/latest/)
- [Keystone Documentation](https://docs.openstack.org/keystone/latest/)
- [Horizon Documentation](https://docs.openstack.org/horizon/latest/)
- [Nova Documentation](https://docs.openstack.org/nova/latest/)
- [Neutron Documentation](https://docs.openstack.org/neutron/latest/)
- [Glance Documentation](https://docs.openstack.org/glance/latest/)
- [Cinder Documentation](https://docs.openstack.org/cinder/latest/)
- [Heat Documentation](https://docs.openstack.org/heat/latest/)
- [Manila Documentation](https://docs.openstack.org/manila/latest/)
- [Helm Documentation](https://helm.sh/docs/helm/helm_install/)
- [PostgreSQL Documentation](https://www.digitalocean.com/community/tutorials/how-to-deploy-postgres-to-kubernetes-cluster)
- [k8s health checks](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/)
- [k8s persistent volumes](https://kubernetes.io/docs/concepts/storage/persistent-volumes/)
"""

#!/usr/bin/env python

# Import the necessary geni-lib libraries.
# geni.portal is used for defining user-configurable parameters.
# geni.rspec.pg is for defining the resources in the ProtoGENI RSpec format.
import geni.portal as portal
import geni.rspec.pg as pg
import geni.rspec.emulab as emulab
import geni.rspec.igext as ig

# Create a portal context object.
# This is the main interface to the CloudLab portal environment.
pc = portal.Context()

# === Profile Parameters ===
# Define user-configurable parameters that will appear
# on the CloudLab instantiation page.

# Parameter for selecting the OS image.
# Note: You can find other images and their URNs at:
# https://www.cloudlab.us/images.php
pc.defineParameter(
    "osImage", "Operating System Image",
    portal.ParameterType.IMAGE,
    "urn:publicid:IDN+emulab.net+image+emulab-ops:UBUNTU24-64-STD",
    longDescription="OS image for all nodes. Ubuntu 24.04 is used here."
)

# Parameter for selecting the physical hardware type.
# An empty string lets CloudLab choose the best available type.
# Specifying a type (e.g., 'd430', 'm510') ensures hardware homogeneity.[11]
pc.defineParameter(
    "hwType", "Hardware Type",
    portal.ParameterType.NODETYPE,
    "d430", # Default to d430 nodes.
    longDescription="Specify a hardware type for all nodes. Clear Selection for any available type."
)

# Parameter for the number of compute nodes.
# The total number of nodes will be this value + 1 (for the controller).
pc.defineParameter(
    "computeNodeCount", "Number of Compute Nodes",
    portal.ParameterType.INTEGER,
    1,
    longDescription="The number of OpenStack compute nodes to provision. Total number of nodes will be n+1 (including controller node). Recommended: 2 or more. Try increasing this if Kubernetes Cluster creation fails due to insufficient resources."
)

# Parameters for OpenStack authentication.
# These will be used in the DevStack configuration.
# Default values are provided for convenience but should be changed.
pc.defineParameter(
    "os_username", "OpenStack Username", 
    portal.ParameterType.STRING, 
    "crookshanks",
    longDescription="Custom username for OpenStack authentication (required). Defaulting to 'crookshanks'."
)

pc.defineParameter(
    "os_password", "OpenStack Password",
    portal.ParameterType.STRING,
    "chocolateFrog!",
    longDescription="Custom password for OpenStack authentication (required). Defaulting to 'chocolateFrog!'."
)

# Retrieve the bound parameters from the portal context.
params = pc.bindParameters()

# === Resource Specification ===
# Create a request object to start building the RSpec.
request = pc.makeRequestRSpec()

# Create a LAN object to connect all nodes.
lan = request.LAN("lan")

# --- Controller Node Definition ---
# This node will run all OpenStack control plane services and
# orchestrate the deployment.
controller = request.RawPC("controller")
controller.disk_image = params.osImage
if params.hwType:
    controller.hardware_type = params.hwType

# Add the controller node to the LAN.
iface_controller = controller.addInterface("if0")
lan.addInterface(iface_controller)

# Add post-boot execution services to the controller node.
# These commands are executed sequentially after the OS boots.
# The repository is cloned to /local/repository automatically.
controller.addService(pg.Execute(shell="sh", command="sudo chmod +x /local/repository/scripts/01-install-openstack.sh"))
controller.addService(pg.Execute(shell="sh", command="sudo -H /local/repository/scripts/01-install-openstack.sh {}".format(params.os_password)))
controller.addService(pg.Execute(shell="sh", command="sudo chmod +x /local/repository/scripts/02-configure-magnum.sh"))
controller.addService(pg.Execute(shell="sh", command="sudo -H /local/repository/scripts/02-configure-magnum.sh"))

# --- Compute Nodes Definition ---
# These nodes will run the OpenStack Nova compute service and host the VMs.
for i in range(params.computeNodeCount):
    node_name = "compute-{}".format(i+1)
    node = request.RawPC(node_name)
    node.disk_image = params.osImage
    if params.hwType:
        node.hardware_type = params.hwType
    
    # Add the compute node to the LAN.
    node.routable_control_ip = True
    iface_compute = node.addInterface("if0")
    lan.addInterface(iface_compute)
    

# Set the instructions to be displayed on the experiment page.
# tour = ig.Tour()
# tour.Description = (ig.Tour.MARKDOWN, description)
# tour.Instructions(ig.Tour.MARKDOWN,instructions)
# request.addTour(tour)

# === Finalization ===
# Print the generated RSpec to the CloudLab portal, which will then use it
# to provision the experiment.
pc.printRequestRSpec(request)
