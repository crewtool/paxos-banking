import schedule
import time
import requests
import google.auth

credentials, project = google.auth.default()

LOADBALANCER_SERVICE_NAME = "node-app-loadbalancer"

def shutdown():
	print("Shutting down")
	requests.post('http://' + LOADBALANCER_SERVICE_NAME + '/shutdown')

schedule.every(600).seconds.do(shutdown)

time.sleep(300)
while 1:
	schedule.run_pending()
	time.sleep(1)
