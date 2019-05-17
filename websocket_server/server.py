import asyncio
import websockets
import json

consumers = set()
console_consumers = set()

# TODO: Here we can also check for invalid lsys messages

# rules stored as tuples: (key, rule)
lsys_rules = []
lsys_axiom = "0"

def reset_lsys():
	global lsys_rules, lsys_axiom
	lsys_rules = []
	lsys_axiom = "0"
reset_lsys()

# implement reset
def parse_lsys(string):
	global lsys_rules, lsys_axiom

	rules = string.strip().split(",")
	for rule in rules:
		pair = rule.split(".")
		# axiom
		if pair[0] == "*":
			if pair[1] == "0":
				reset_lsys()
			else:
				lsys_axiom = pair[1]
		else:
			rules_list = list(filter(lambda x: x[0] != pair[0], lsys_rules))
			lsys_rules = [pair]
			lsys_rules.extend(rules_list)

def serialize_lsys():
	ret = ["*." + lsys_axiom]
	ret_list = lsys_rules.copy()
	ret_list.reverse()
	ret.extend(map(lambda x: x[0] + "." + x[1], ret_list))
	return ",".join(ret)

async def register_code_consumer(websocket):
	console_consumers.add(websocket)
	print("Connected Console Consumers: " + str(len(console_consumers)))

async def register_consumer(websocket):
	consumers.add(websocket)
	print("Connected Consumers: " + str(len(consumers)))

async def unregister_consumer(websocket):
	consumers.remove(websocket)
	if websocket in console_consumers:
		console_consumers.remove(websocket)
	print("Disconnect!")

def send_console(code):
	msg = json.dumps({"type": "code", "payload": code})
	for websocket in console_consumers:
		websocket.send(msg)

async def send_lsys(websocket, msg):
	print(websocket)
	print(msg)
	await websocket.send(msg)


async def broadcast_lsys():
	msg = json.dumps({"type": "lsys", "payload": serialize_lsys()})
	await asyncio.wait([websocket.send(msg) for websocket in consumers])


async def ckar(websocket, path):
	print(path)
	if path == "/ckar_consume":
		await send_lsys(websocket, json.dumps({"type": "lsys", "payload": serialize_lsys()}))
		await register_consumer(websocket)
		try:
			async for message in websocket:
				msg = json.loads(message)
				if msg["type"] == "subscribe" and msg["payload"] == "console":
					register_console_consumer(websocket)
		except websockets.exceptions.ConnectionClosed:
			pass
		finally:
			await unregister_consumer(websocket)

	if path == "/ckar_serve":
		try:
			print("Connected Server!")
			async for message in websocket:
				print("IN: " + message)
				msg = json.loads(message)
				if msg["type"] == "console":
					send_console(msg["payload"])
				if msg["type"] == "lsys":
					parse_lsys(msg["payload"])
					await broadcast_lsys()
		except websockets.exceptions.ConnectionClosed:
			pass
		finally:
			print("Disconnected Server!")

start_server = websockets.serve(ckar, '192.168.178.235', 8081)
asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()