import asyncio
import websockets
import json
import socket
import os

from netstuff import *

STATE_FILE = "lsys-state.txt"

PORT = 8081
HOST = None

if HOST == None:
	s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	s.connect(("8.8.8.8", 80))
	HOST = s.getsockname()[0]
	s.close()

announce_server(HOST, PORT)

# START

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

def load_lsys():
	if os.path.isfile(STATE_FILE):
		with open(STATE_FILE, "r", encoding="utf-8") as file:
			parse_lsys(file.read())
			print("Loaded LSys: " + serialize_lsys())
	else:
		reset_lsys()
load_lsys()

def store_lsys():
	with open(STATE_FILE, 'w', encoding='utf-8') as file:
		file.write(serialize_lsys())





def register_console_consumer(websocket):
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

async def broadcast_console(console):
	msg = json.dumps({"type": "console", "payload": console})
	await asyncio.wait([websocket.send(msg) for websocket in console_consumers])

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
				if msg["type"] == "console" and len(console_consumers) > 0:
					await broadcast_console(msg["payload"])
				if msg["type"] == "lsys" and len(consumers) > 0:
					parse_lsys(msg["payload"])
					store_lsys()
					await broadcast_lsys()
		except websockets.exceptions.ConnectionClosed:
			pass
		finally:
			print("Disconnected Server!")

start_server = websockets.serve(ckar, HOST, PORT)
asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()