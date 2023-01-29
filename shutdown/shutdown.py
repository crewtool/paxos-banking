import schedule
import time
import requests
import google.auth

credentials, project = google.auth.default()

INTERNAL_SERVICE_NAME = "node-app-internal"

def shutdown():
	print("Shutting down")
	requests.post('http://' + INTERNAL_SERVICE_NAME + '/shutdown')

schedule.every(1200).seconds.do(shutdown)

time.sleep(1200)
while 1:
	schedule.run_pending()
	time.sleep(1)
