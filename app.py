import os

import google.auth
import uuid
from google.auth.transport.requests import AuthorizedSession
from google.cloud import firestore
from flask import Flask, request, jsonify
app = Flask(__name__)

@app.route('/')
def hello_world():
    target = os.environ.get('TARGET', 'World')
    return 'Hello {}!\n'.format(target)

# Set up the Firestore client
credentials, project = google.auth.default()
db = firestore.Client(project=project, credentials=credentials)

# Banking system

def check_account(account_id):
  # Get the account from Firestore
  doc_ref = db.collection("accounts").document(account_id)
  doc = doc_ref.get()
  if doc.exists:
    return doc.to_dict()["balance"]
  else:
    return "Account not found."

def withdraw_money(account_id, amount):
  # Get the account from Firestore
  doc_ref = db.collection("accounts").document(account_id)
  doc = doc_ref.get()
  if doc.exists:
    balance = doc.to_dict()["balance"]
    if balance >= amount:
      # Update the account balance in Firestore
      doc_ref.update({"balance": balance - amount})
      return "Withdrawal successful."
    else:
      return "Insufficient funds."
  else:
    return "Account not found."

def open_account():
  # Generate a new UUID for the account
  account_id = str(uuid.uuid4())
  # Create the new account in Firestore
  doc_ref = db.collection("accounts").document(account_id)
  doc_ref.set({"balance": 0})
  return account_id

def move_money(from_account_id, to_account_id, amount):
  # Get the accounts from Firestore
  from_doc_ref = db.collection("accounts").document(from_account_id)
  from_doc = from_doc_ref.get()
  to_doc_ref = db.collection("accounts").document(to_account_id)
  to_doc = to_doc_ref.get()
  if from_doc.exists and to_doc.exists:
    from_balance = from_doc.to_dict()["balance"]
    if from_balance >= amount:
      # Update the account balances in Firestore
      from_doc_ref.update({"balance": from_balance - amount})
      to_doc_ref.update({"balance": to_doc.to_dict()["balance"] + amount})
      return "Money moved successfully."
    else:
      return "Insufficient funds."
  else:
    return "One or more accounts not found."

def add_money(account_id, amount):
  # Get the account from Firestore
  doc_ref = db.collection("accounts").document(account_id)
  doc = doc_ref.get()
  if doc.exists:
    # Update the account balance in Firestore
    doc_ref.update({"balance": doc.to_dict()["balance"] + amount})
    return "Money added successfully."
  else:
    return "Account not found."

# Endpoints

@app.route("/check_account", methods=["GET"])
def check_account_endpoint():
  account_id = request.args.get("account_id")
  balance = check_account(account_id)
  return jsonify({"balance": balance})

@app.route("/withdraw_money", methods=["POST"])
def withdraw_money_endpoint():
  data = request.get_json()
  account_id = data["account_id"]
  amount = data["amount"]
  result = withdraw_money(account_id, amount)
  return jsonify({"result": result})

@app.route("/open_account", methods=["POST"])
def open_account_endpoint():
  account_id = open_account()
  return jsonify({"account_id": account_id})

@app.route("/move_money", methods=["POST"])
def move_money_endpoint():
  data = request.get_json()
  from_account_id = data["from_account_id"]
  to_account_id = data["to_account_id"]
  amount = data["amount"]
  result = move_money(from_account_id, to_account_id, amount)
  return jsonify({"result": result})


@app.route("/add_money", methods=["POST"])
def add_money_endpoint():
  data = request.get_json()
  account_id = data["account_id"]
  amount = data["amount"]
  result = add_money(account_id, amount)
  return jsonify({"result": result})

if __name__ == "__main__":
    app.run(debug=True,host='0.0.0.0',port=int(os.environ.get('PORT', 8080)))
    

