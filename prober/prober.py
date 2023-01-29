import google.auth
from google.cloud import firestore
from kubernetes import client, config
import os
import requests
from requests import Timeout, RequestException, ConnectionError
import time

EXTERNAL_SERVICE_NAME = "node-app-external"
INTERNAL_SERVICE_NAME = "node-app-internal"
NAMESPACE = "default"
HEALTHCHECK_INTERVAL = 30
LEADER_SYSTEM = not (os.environ["LEADER_SYSTEM"] == "False" or os.environ["LEADER_SYSTEM"] == "0")

round_id = -1

# Load the Kubernetes configuration and get client
config.load_incluster_config()
client_v1 = client.CoreV1Api()

# Set up the Firestore client
credentials, project = google.auth.default()
db = firestore.Client(project=project, credentials=credentials)

def initialize():
	update_selector(1, EXTERNAL_SERVICE_NAME, NAMESPACE)
	accounts_ref = db.collection("accounts")
	account_ref = accounts_ref.document("prober")
	if not account_ref.get().exists:
		accounts_ref.document("prober").set({"balance": 0.0})

def update_selector(selector, service_name, namespace):
	new_selector = {"id": str(selector)}
	service = client_v1.read_namespaced_service(service_name, namespace)
	service.spec.selector = new_selector
	client_v1.patch_namespaced_service(service_name, namespace, service)

def healthcheck_error():
	if not LEADER_SYSTEM:
		return
	global round_id
	round_id += 1
	while True:
		try:
			response = requests.post('http://' + INTERNAL_SERVICE_NAME + '/elect_new_leader',
				json={"round_id": round_id}, timeout=60)
		except Timeout:
			continue
		if response.status_code != 200:
			continue
		selector_num = int(response.json())
		break
	update_selector(selector_num, EXTERNAL_SERVICE_NAME, NAMESPACE)
	return str(selector_num)

def healthcheck():
	while True:
		try:
			response = requests.post("http://" + EXTERNAL_SERVICE_NAME + "/deposit_money",
				json={"account_id": "prober", "amount": 1}, timeout=5)
		except Timeout:
			healthcheck_error()
			return "Timeout has been raised"
		except ConnectionError:
			healthcheck_error()
			return "Connection error"
		except RequestException:
			time.sleep(1)
			continue
		if response.status_code != 200:
			healthcheck_error()
			return "Error response status code"
		break
	return "Health checking..."

initialize()
while True:
	healthcheck()
	time.sleep(HEALTHCHECK_INTERVAL)
