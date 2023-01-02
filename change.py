from kubernetes import client, config

# Load the Kubernetes configuration
config.load_kube_config()

# Create a client for the CoreV1 API
v1 = client.CoreV1Api()

# Define the name and namespace of the service you want to update
service_name = "hello"
namespace = "default"

# Define the new selector for the service
new_selector = {"app": "hello3"}

# Get the current configuration of the service
service = v1.read_namespaced_service(service_name, namespace)

# Update the service's selector
service.spec.selector = new_selector

# Patch the service using the updated configuration
v1.patch_namespaced_service(service_name, namespace, service)

