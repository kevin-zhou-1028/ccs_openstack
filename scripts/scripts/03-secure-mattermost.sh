#!/bin/bash

# Apply NetworkPolicy
kubectl apply -f /home/core/<repo-folder>/k8s-manifests/01-mattermost-networkpolicy.yaml

# Create TLS secret for Ingress (self-signed)
kubectl create secret tls mattermost-tls \
  --cert=/home/core/<repo-folder>/tls/server.crt \
  --key=/home/core/<repo-folder>/tls/server.key \
  -n mattermost

echo "NetworkPolicy and TLS applied!"

