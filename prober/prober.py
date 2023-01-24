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
	if not account_ref.get().exists:
		accounts_ref.document("prober").set({"balance": 0})

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
	try:
		response = requests.post('http://' + SERVICE_NAME + '/add_money', json={"account_id": "prober", "amount": 1},
								 timeout=5)
	except Timeout:
		run_paxos()
		return "Timeout has been raised.."
	except ConnectionError:
		run_paxos()
		return "Connection error"
	except RequestException:
		time.sleep(1)
		response = requests.post('http://'
								 + SERVICE_NAME + '/add_money', json={"account_id": "prober", "amount": 1},
								 timeout=5)

	if response.status_code != 200:
		run_paxos()

	return "Health checking..."

schedule.every(SCHEDULE_SECONDS).seconds.do(healthcheck)
initialize()
while True:
	schedule.run_pending()
	time.sleep(1)
