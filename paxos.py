import asyncio
import aiohttp
from quart import Quart, jsonify, request

app = Quart(__name__)

# TODO: uzupełnić brakujące dane
nodes = []
quorum = len(nodes) // 2 + 1
node_id = 0

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
		proposal_id = self.node_id - len(nodes)
		while True:
			proposal_id += len(nodes)
			proposal = {"round_id": self.round_id, "proposal_id": proposal_id}
			async with aiohttp.ClientSession() as session:
				promises = await asyncio.gather(*[
					post(session, "http://" + node + "/leader_proposal", json=proposal, timeout=self.timeout)
					for node in nodes
				])
				promises = list(filter(lambda x: x is not None, promises))
				if len(promises) < quorum:
					continue

				accepted_id = -1
				accepted_node = self.node_id
				for promise in promises:
					accepted = promise["accepted"]
					if accepted is not None:
						if accepted["id"] > accepted_id:
							accepted_id = accepted["id"]
							accepted_node = accepted["node"]
				accept_request = {"round_id": self.round_id, "proposal_id": self.proposal_id, "node_id": accepted_node}
				accepts = await asyncio.gather(*[
					post(session, "http://" + node + "/leader_request", json=accept_request, timeout=self.timeout)
					for node in nodes
				])
				accepts = list(filter(lambda x: x is not None, accepts))
				if len(accepts) < quorum:
					continue

				return accepted_node

	async def handle_proposal(self, proposal_id):
		if proposal_id < self.ignored_ids:
			return
		self.ignored_ids = proposal_id
		promise = {"accepted": self.accepted}
		return promise

	async def handle_request(self, proposal_id, node_id):
		if proposal_id < self.ignored_ids:
			return
		self.accepted = {"id": proposal_id, "node": node_id}
		return jsonify(True)

@app.route("/elect_new_leader", methods=["POST"])
async def elect_new_leader():
	global round_id
	global leader_election
	global node_id
	json = await request.get_json()
	round_id = json["round_id"]
	leader_election = LeaderElection(round_id, node_id, 5.)
	return await leader_election.propose_self()

@app.route("/leader_proposal", methods=["POST"])
async def handle_proposal():
	global round_id
	global leader_election
	json = await request.get_json()
	if round_id != json["round_id"]:
		return
	return await leader_election.handle_proposal(json["proposal_id"])

@app.route("/leader_request", methods=["POST"])
async def handle_request():
	global round_id
	global leader_election
	json = await request.get_json()
	if round_id != json["round_id"]:
		return
	return await leader_election.handle_request(json["proposal_id"], json["node_id"])

async def post(session, url, **kwargs):
	try:
		async with session.request("POST", url, **kwargs) as response:
			return await response.text()
	except aiohttp.ClientError:
		pass

if __name__ == "__main__":
	app.run()
