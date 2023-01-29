from flask import Flask, request, jsonify, render_template
import google.auth
from google.cloud import firestore
import os
import requests
import subprocess
import uuid

app = Flask(__name__)

NODE_ID = int(os.environ["NODE_ID"])
PAXOS_PORT = int(os.environ["PAXOS_PORT"])
PAXOS_HOST = f"http://localhost:{PAXOS_PORT}"
LEADER_SYSTEM = bool(os.environ["LEADER_SYSTEM"])

# Set up the Firestore client
credentials, project = google.auth.default()
db = firestore.Client(project=project, credentials=credentials)

# Banking system

def initialize():
	meta_ref = get_meta_ref()
	if not meta_ref.get().exists:
		meta_ref.set({"last_operation_id": 0})

def get_accounts_ref():
	if LEADER_SYSTEM:
		name = "accounts"
	else:
		name = "accounts-" + str(NODE_ID)
	return db.collection(name)

def get_meta_ref():
	return get_accounts_ref().document("meta")

def check_account(account_id):
	doc_ref = get_accounts_ref().document(account_id)
	doc = doc_ref.get()
	if doc.exists:
		return doc.get("balance")
	else:
		return "Account not found."

def open_account(data):
	# Generate a new UUID for the account
	account_id = str(uuid.uuid4())

	# Create the new account in Firestore
	doc_ref = get_accounts_ref().document(account_id)
	meta_ref = get_meta_ref()
	@firestore.transactional
	def open_account_transactional(transaction, doc_ref, meta_ref):
		meta = transaction.get(meta_ref)
		transaction.update(meta_ref, {"last_operation_id": meta.get("last_operation_id") + 1})
		transaction.set(doc_ref, {"balance": 0.0})

	open_account_transactional(db.transaction(), doc_ref, meta_ref)
	return jsonify({"account_id": account_id})

def deposit_money(data):
	data = request.get_json()
	account_id = data["account_id"]
	amount = data["amount"]

	doc_ref = get_accounts_ref().document(account_id)
	meta_ref = get_meta_ref()
	@firestore.transactional
	def add_money_transactional(transaction, doc_ref, meta_ref):
		doc = transaction.get(doc_ref)
		meta = transaction.get(meta_ref)
		transaction.update(meta_ref, {"last_operation_id": meta.get("last_operation_id") + 1})
		if doc.exists:
			# Update the account balance in Firestore
			transaction.update(doc_ref, {"balance": doc.get("balance") + amount})
			return "Money added successfully."
		else:
			return "Account not found."

	result = add_money_transactional(db.transaction(), doc_ref, meta_ref)
	return jsonify({"result": result})

def withdraw_money(data):
	account_id = data["account_id"]
	amount = data["amount"]

	doc_ref = get_accounts_ref().document(account_id)
	meta_ref = get_meta_ref()
	@firestore.transactional
	def withdraw_money_transactional(transaction, doc_ref, meta_ref):
		doc = transaction.get(doc_ref)
		meta = transaction.get(meta_ref)
		transaction.update(meta_ref, {"last_operation_id": meta.get("last_operation_id") + 1})
		if doc.exists:
			if doc.get("balance") >= amount:
				# Update the account balance in Firestore
				transaction.update(doc_ref, {"balance": doc.get("balance") - amount})
				return "Withdrawal successful."
			else:
				return "Insufficient funds."
		else:
			return "Account not found."

	result = withdraw_money_transactional(db.transaction(), doc_ref, meta_ref)
	return jsonify({"result": result})

def move_money(data):
	data = request.get_json()
	source = data["source"]["account_id"]
	destination = data["destination"]["account_id"]
	amount = data["amount"]

	from_doc_ref = get_accounts_ref().document(source)
	to_doc_ref = get_accounts_ref().document(destination)
	meta_ref = get_meta_ref()
	@firestore.transactional
	def move_money_transactional(transaction, from_doc_ref, to_doc_ref, meta_ref):
		from_doc = transaction.get(from_doc_ref)
		to_doc = transaction.get(to_doc_ref)
		meta = transaction.get(meta_ref)
		transaction.update(meta_ref, {"last_operation_id": meta.get("last_operation_id") + 1})
		if from_doc.exists and to_doc.exists:
			if from_doc.get("balance") >= amount:
				# Update the account balances in Firestore
				transaction.update(from_doc_ref, {"balance": from_doc.get("balance") - amount})
				transaction.update(to_doc_ref, {"balance": to_doc.get("balance") + amount})
				return "Money moved successfully."
			else:
				return "Insufficient funds."
		else:
			return "One or more accounts not found."

	result =  move_money_transactional(db.transaction(), from_doc_ref, to_doc_ref, meta_ref)
	return jsonify({"result": result})

def get_last_operation_id():
	accounts_ref = get_accounts_ref()
	return accounts_ref.document("meta").get("last_operation_id")

# Endpoints

@app.route('/')
def front():
	collection = get_accounts_ref()
	docs = collection.get()
	rows = []
	for doc in docs:
		if doc.id != "leader" and doc.id != "prober":
			rows.append({"account_id": doc.id, **doc.to_dict()})
	return render_template(
		'index.tmpl',
		rows=rows,
		leader=NODE_ID
	)

operations = {}

def apply_banking_operation(operation):
	kind = operation["kind"]
	data = operation["data"]
	match kind:
		case "open_account":
			result = open_account(data)
		case "deposit_money":
			result = deposit_money(data)
		case "withdraw_money":
			result = withdraw_money(data)
		case "move_money":
			result = move_money(data)
	return result

def do_banking_operation(operation_id, operation):
	global last_operation_id
	next_operation_id = get_last_operation_id() + 1
	if operation_id < next_operation_id:
		return None
	elif operation_id > next_operation_id:
		operations[operation_id] = operation
		return None

	result = apply_banking_operation(operation)
	next_operation_id = get_last_operation_id() + 1
	while True:
		next_operation = operations.pop(next_operation_id, None)
		if next_operation:
			apply_banking_operation(operation)
			next_operation_id = get_last_operation_id() + 1
		else:
			break
	return result

def banking_operation(operation):
	while True:
		operation_id = get_last_operation_id() + 1
		uuid = uuid.uuid4()
		value = {"uuid": uuid, "operation": operation}
		res = requests.post(f"{PAXOS_HOST}/paxos_new", json={"round_id": operation_id, "value": value})
		applied_operation = res.json()
		response = do_banking_operation(operation_id, applied_operation["operation"])
		if applied_operation["uuid"] == uuid:
			#TODO: inform all
			break
	return jsonify(response)

@app.route("/learn_banking_operation", methods=["POST"])
def learn_banking_operation():
	json = request.get_json()
	operation_id = json["operation_id"]
	operation = json["operation"]
	do_banking_operation(operation_id, operation)
	return ""

@app.route("/check_account", methods=["GET"])
def check_account_endpoint():
	account_id = request.args.get("account_id")
	balance = check_account(account_id)
	return jsonify({"balance": balance})

@app.route("/open_account", methods=["POST"])
def open_account_endpoint():
	json = request.get_json()
	if LEADER_SYSTEM:
		return open_account(json)
	else:
		operation = {"kind": "open_account", "data": json}
		return banking_operation(operation)

@app.route("/deposit_money", methods=["POST"])
def deposit_money_endpoint():
	json = request.get_json()
	if LEADER_SYSTEM:
		return deposit_money(json)
	else:
		operation = {"kind": "deposit_money", "data": json}
		return banking_operation(operation)

@app.route("/withdraw_money", methods=["POST"])
def withdraw_money_endpoint():
	json = request.get_json()
	if LEADER_SYSTEM:
		return withdraw_money(json)
	else:
		operation = {"kind": "withdraw_money", "data": json}
		return banking_operation(operation)

@app.route("/move_money", methods=["POST"])
def move_money_endpoint():
	json = request.get_json()
	if LEADER_SYSTEM:
		return move_money(json)
	else:
		operation = {"kind": "move_money", "data": json}
		return banking_operation(operation)

@app.route("/elect_new_leader", methods=["POST"])
def elect_new_leader():
	if LEADER_SYSTEM:
		data = request.get_json()
		round_id = data["round_id"]
		response = requests.post(f"{PAXOS_HOST}/paxos_new", json={"round_id": round_id, "value": NODE_ID})
		return jsonify(response.json())

@app.route("/shutdown", methods=["POST"])
def shutdown():
	subprocess.run(["pkill", "gunicorn"])
	return 'Server shutting down...'

initialize()
if __name__ == "__main__":
	app.run(debug=True)
