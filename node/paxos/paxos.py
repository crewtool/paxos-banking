import asyncio
import aiohttp
from quart import Quart, abort, jsonify, request
import os
import sys

app = Quart(__name__)

NODE_ID = int(os.environ["NODE_ID"])
NODES_COUNT = int(os.environ["NODES_COUNT"])
PAXOS_PREFIX = "node-paxos-"
NODES = [PAXOS_PREFIX + str(i) for i in range(1, NODES_COUNT + 1)]
QUORUM = NODES_COUNT // 2 + 1
GENERAL_TIMEOUT = 5.

round_id = -1
leader_election = None

class LeaderElection:
	def __init__(self, round_id, node_id, general_timeout):
		self.timeout = general_timeout
		self.node_id = node_id
		self.round_id = round_id
		self.ignored_ids = 0
		self.accepted = None

	async def propose_self(self):
		proposal_id = self.node_id - NODES_COUNT
		while True:
			proposal_id += NODES_COUNT
			proposal = {"round_id": self.round_id, "proposal_id": proposal_id}
			async with aiohttp.ClientSession() as session:
				promises = await asyncio.gather(*[
					post(session, "http://" + node + "/leader_proposal", json=proposal, timeout=self.timeout)
					for node in NODES
				])
				promises = list(filter(lambda x: x, promises))
				eprint(f"propose_self promises {promises}")
				if len(promises) < QUORUM:
					continue

				accepted_id = -1
				accepted_node = self.node_id
				for promise in promises:
					accepted = promise["accepted"]
					if accepted is not None:
						if accepted["id"] > accepted_id:
							accepted_id = accepted["id"]
							accepted_node = accepted["node"]
				accept_request = {"round_id": self.round_id, "proposal_id": proposal_id, "node_id": accepted_node}
				accepts = await asyncio.gather(*[
					post(session, "http://" + node + "/leader_request", json=accept_request, timeout=self.timeout)
					for node in NODES
				])
				accepts = list(filter(lambda x: x, accepts))
				eprint(f"propose_self accepts {accepts}")
				if len(accepts) < QUORUM:
					continue

				return jsonify(accepted_node)

	async def handle_proposal(self, proposal_id):
		if proposal_id < self.ignored_ids:
			return jsonify(None)
		self.ignored_ids = proposal_id
		promise = {"accepted": self.accepted}
		eprint(f"handle_proposal {promise}")
		return promise

	async def handle_request(self, proposal_id, node_id):
		if proposal_id < self.ignored_ids:
			return jsonify(None)
		self.accepted = {"id": proposal_id, "node": node_id}
		eprint(f"handle_request {True}")
		return jsonify(True)

@app.route("/elect_new_leader", methods=["POST"])
async def elect_new_leader():
	global leader_election
	json = await request.get_json()
	eprint(f"elect_new_leader {json['round_id']}")
	get_leader_election(json["round_id"])
	return await leader_election.propose_self()

@app.route("/leader_proposal", methods=["POST"])
async def handle_proposal():
	global leader_election
	json = await request.get_json()
	eprint(f"leader_proposal {json['round_id']} {json['proposal_id']}")
	get_leader_election(json["round_id"])
	return await leader_election.handle_proposal(json["proposal_id"])

@app.route("/leader_request", methods=["POST"])
async def handle_request():
	global leader_election
	json = await request.get_json()
	eprint(f"leader_request {json['round_id']} {json['proposal_id']} {json['node_id']}")
	get_leader_election(json["round_id"])
	return await leader_election.handle_request(json["proposal_id"], json["node_id"])

def get_leader_election(new_round_id):
	global round_id
	global leader_election
	if round_id > new_round_id:
		abort(409)
	elif round_id < new_round_id:
		round_id = new_round_id
		leader_election = LeaderElection(round_id, NODE_ID, GENERAL_TIMEOUT)

async def post(session, url, **kwargs):
	try:
		async with session.request("POST", url, **kwargs) as response:
			return await response.json()
	except aiohttp.ClientError:
		pass
	except asyncio.TimeoutError:
		pass

def eprint(*args, **kwargs):
	print(*args, file=sys.stderr, **kwargs)

if __name__ == "__main__":
	app.run()
