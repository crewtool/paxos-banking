#!/bin/bash

project_id=$(gcloud config get-value project --verbosity none)
if [ -z "$project_id" ]; then
  echo "No project id."
  exit 1
fi

count=$1
leader_system=$2
if [ -z "$count" ]; then
  count=7
fi
if [ -z "$leader_system" ]; then
  leader_system=True
fi

echo "Generating kubernetes resources from templates..."
cp -r k8s k8s-apply
for i in $(seq 1 $count); do
  jinja2 node/deployment.tmpl -D project_id=$project_id -D number=$i -D count=$count -D leader_system=$leader_system > k8s-apply/node-$i.yaml
done
jinja2 prober/deployment.tmpl -D project_id=$project_id -D number=$i -D count=$count -D leader_system=$leader_system > k8s-apply/prober.yaml
jinja2 shutdown/deployment.tmpl -D project_id=$project_id > k8s-apply/shutdown.yaml

echo "Creating K8s resources..."
gcloud container clusters create-auto banking-cluster --region europe-central2
kubectl create secret generic banking-key --from-file=key.json=bankingkey.json
kubectl create serviceaccount banking-sa
kubectl apply -f k8s-apply/manage-services-role.yaml
kubectl create rolebinding manage-serives-bind --clusterrole=manage-services-role --serviceaccount=default:banking-sa
# kubectl apply -f k8s-apply
