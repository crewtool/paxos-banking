import os
import schedule
import time
import requests
import logging
import google.auth
from google.cloud import firestore
from kubernetes import client, config
import random

from requests import Timeout, RequestException, ConnectionError

credentials, project = google.auth.default()
db = firestore.Client(project=project, credentials=credentials)

# Load the Kubernetes configuration and get client
config.load_incluster_config()
client_v1 = client.CoreV1Api()

SERVICE_NAME = os.environ.get("SERVICE_NAME", "banking-service-lb")
NAMESPACE = os.environ.get("NAMESPACE", "default")
SELECTOR_PREFIX = os.environ.get("SELECTOR_PREFIX", "banking")

SCHEDULE_SECONDS = int(os.environ.get("SCHEDULE_SECONDS", 15))
round_id = -1

def initialize():
	accounts_ref = db.collection("accounts")
	account_ref = accounts_ref.document("prober")
	leader_ref = accounts_ref.document("leader")
	if not account_ref.get().exists:
		accounts_ref.document("prober").set({"balance": 0})

	if not leader_ref.get().exists:
		accounts_ref.document("leader").set({"selector": SELECTOR_PREFIX + "-1", "is_selector_set": True})

def update_selector(selector, service_name, namespace):
	new_selector = {"app": selector}
	service = client_v1.read_namespaced_service(service_name, namespace)
	service.spec.selector = new_selector
	client_v1.patch_namespaced_service(service_name, namespace, service)

def run_paxos():
	global round_id
	round_id += 1
	response = requests.post('http://' + SERVICE_NAME + '/elect_new_leader', json={"round_id": round_id}, timeout=60)
	selector_num = int(response)
	update_selector(SELECTOR_PREFIX + "-" + str(selector_num), SERVICE_NAME, NAMESPACE)
	return SELECTOR_PREFIX + "-" + str(selector_num)

def healthcheck():
	accounts_ref = db.collection("accounts")
	leader_ref = accounts_ref.document("leader")
	doc = leader_ref.get()
	selector = doc.get("selector")

	if selector == "ERROR":
		new_selector = run_paxos()
		accounts_ref.document("leader").set({"selector": new_selector, "is_selector_set": True})
		return "Paxos run"

	if not doc.get("is_selector_set"):
		update_selector(selector, SERVICE_NAME, NAMESPACE)
		accounts_ref.document("leader").set({"selector": selector, "is_selector_set": True})

	try:
		response = requests.post('http://' + SERVICE_NAME + '/add_money', json={"account_id": "prober", "amount": 1},
								 timeout=5)
	except Timeout:
		new_selector = run_paxos()
		accounts_ref.document("leader").set({"selector": new_selector, "is_selector_set": False})
		return "Timeout has been raised.."
	except ConnectionError:
		new_selector = run_paxos()
		accounts_ref.document("leader").set({"selector": new_selector, "is_selector_set": False})
		return "Connection error"
	except RequestException:
		time.sleep(1)
		response = requests.post('http://'
								 + SERVICE_NAME + '/add_money', json={"account_id": "prober", "amount": 1},
								 timeout=5)

	if response.status_code != 200:
		accounts_ref.document("leader").set({"selector": "ERROR", "is_selector_set": False})
		run_paxos()

	return "Health checking..."

schedule.every(SCHEDULE_SECONDS).seconds.do(healthcheck)
initialize()
while True:
	schedule.run_pending()
	time.sleep(1)
