import asyncio
import aiohttp
from quart import Quart, abort, jsonify, request
import os
from random import uniform
import sys

app = Quart(__name__)

NODE_ID = int(os.environ["NODE_ID"])
NODES_COUNT = int(os.environ["NODES_COUNT"])
PAXOS_PREFIX = "node-paxos-"
NODES = [PAXOS_PREFIX + str(i) for i in range(1, NODES_COUNT + 1)]
QUORUM = NODES_COUNT // 2 + 1
GENERAL_TIMEOUT = 5.
BACKOFF_BASE = 2.
DEBUG = bool(os.environ.get("DEBUG"))

paxoses = {}

class Paxos:
	def __init__(self, round_id, general_timeout):
		self.timeout = general_timeout
		self.round_id = round_id
		self.ignored_ids = 0
		self.accepted = None
		self.consensus = None

	async def propose(self, value):
		if self.consensus:
			return jsonify(self.consensus)
		proposal_id = NODE_ID - NODES_COUNT
		backoff = BACKOFF_BASE
		while True:
			proposal_id += NODES_COUNT
			proposal = {"round_id": self.round_id, "proposal_id": proposal_id}
			async with aiohttp.ClientSession() as session:
				promises = await asyncio.gather(*[
					post(session, "http://" + node + "/paxos_proposal", json=proposal, timeout=self.timeout)
					for node in NODES
				])
				promises = list(filter(lambda x: x, promises))
				eprint(f"propose_self promises {promises}")
				if len(promises) < QUORUM:
					await asyncio.sleep(uniform(backoff / 2, backoff))
					backoff *= 2
					continue

				accepted_id = -1
				accepted_value = value
				for promise in promises:
					accepted = promise["accepted"]
					if accepted is not None:
						if accepted["id"] > accepted_id:
							accepted_id = accepted["id"]
							accepted_value = accepted["value"]
				accept_request = {"round_id": self.round_id, "proposal_id": proposal_id, "value": accepted_value}
				accepts = await asyncio.gather(*[
					post(session, "http://" + node + "/paxos_request", json=accept_request, timeout=self.timeout)
					for node in NODES
				])
				accepts = list(filter(lambda x: x, accepts))
				eprint(f"propose_self accepts {accepts}")
				if len(accepts) < QUORUM:
					await asyncio.sleep(uniform(backoff / 2, backoff))
					backoff *= 2
					continue

				self.accepted = {"id": self.ignored_ids, "value": accepted_value}
				self.consensus = accepted_value
				return jsonify(accepted_value)

	async def handle_proposal(self, proposal_id):
		if proposal_id < self.ignored_ids:
			return jsonify(None)
		self.ignored_ids = proposal_id
		promise = {"accepted": self.accepted}
		eprint(f"handle_proposal {promise}")
		return promise

	async def handle_request(self, proposal_id, value):
		if proposal_id < self.ignored_ids:
			return jsonify(None)
		self.accepted = {"id": proposal_id, "value": value}
		eprint(f"handle_request {True}")
		return jsonify(True)

@app.route("/paxos_new", methods=["POST"])
async def handle_new():
	json = await request.get_json()
	eprint(f"paxos_new {json['round_id']} {json['value']}")
	paxos = get_paxos(json["round_id"])
	value = json["value"]
	return await paxos.propose(value)

@app.route("/paxos_proposal", methods=["POST"])
async def handle_proposal():
	json = await request.get_json()
	eprint(f"paxos_proposal {json['round_id']} {json['proposal_id']}")
	paxos = get_paxos(json["round_id"])
	return await paxos.handle_proposal(json["proposal_id"])

@app.route("/paxos_request", methods=["POST"])
async def handle_request():
	json = await request.get_json()
	eprint(f"paxos_request {json['round_id']} {json['proposal_id']} {json['value']}")
	paxos = get_paxos(json["round_id"])
	return await paxos.handle_request(json["proposal_id"], json["value"])

def get_paxos(new_round_id):
	return paxoses.setdefault(new_round_id, Paxos(new_round_id, GENERAL_TIMEOUT))

async def post(session, url, **kwargs):
	try:
		async with session.request("POST", url, **kwargs) as response:
			return await response.json()
	except aiohttp.ClientError:
		pass
	except asyncio.TimeoutError:
		pass

def eprint(*args, **kwargs):
	if DEBUG:
		print(*args, file=sys.stderr, **kwargs)

if __name__ == "__main__":
	app.run(debug=True)
