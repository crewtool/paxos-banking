import schedule
import time
import requests
import google.auth
from google.cloud import firestore
from google.auth.transport.requests import AuthorizedSession

credentials, project = google.auth.default()



def shutdown():
	accounts_ref = db.collection("accounts")
	leader_ref = accounts_ref.document("leader")
	if not leader_ref.get().exists:
		accounts_ref.document("leader").set({"value": -1})
		return "Document created."
	else:
		doc = leader_ref.get()
		if doc.get("value") == -1:
			accounts_ref.document("leader").set({"value": 1})
			run_paxos()
		else:
			if not accounts_ref.document("prober").get().exists:
				accounts_ref.document("prober").set({"balance": -1})

			response = requests.post('http://192.168.1.5:8080/add_money', json={"account_id": "prober", "amount": 1})
			# accounts_ref.document("leader").set({"value": -1})
			print(response)
			print(doc.get("value"))
		return "Document already exists."


schedule.every(30).seconds.do(check_and_create)

while 1:
	schedule.run_pending()
	time.sleep(1)
