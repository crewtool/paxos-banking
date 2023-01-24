#!/bin/bash

echo "Building images..."
gcloud builds submit --config build.yaml .

count=3
echo "Generating kubernetes resources from templates..."
for n in {1..$count}
do
  jinja2 node/deployment.tmpl -D project_id=$project_id -D number=$n -D count=$count > k8s/node-$n.yaml
done
jinja2 probler/prober.tmpl -D project_id=$project_id -D number=$n -D count=$count > k8s/prober.yaml

echo "Creating K8s resources..."
gcloud container clusters create-auto banking-cluster --region europe-central2
kubectl create secret generic banking-key --from-file=key.json=bankingkey.json
kubectl create serviceaccount banking-sa
kubectl apply -f k8s/manage-services-role.yaml
kubectl create rolebinding manage-serives-bind --clusterrole=manage-services-role --serviceaccount=default:banking-sa
kubectl apply -f k8s
