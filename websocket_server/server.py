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

# TODO: Here we can also check for invalid lsys messages


# START

consumer_categories = ["basic", "console", "view"]
consumers = {}
for category in consumer_categories:
	consumers[category] = set()

forrest = {}

def empty_lsys():
	return {"axiom": 0, "rules": []}

def reset_forrest():
	global forrest
	forrest = {}
	forrest["0"] = empty_lsys()

def reset_lsys(lsys):
	fresh = empty_tree
	lsys["axiom"] = fresh["axiom"]
	lsys["rules"] = fresh["rules"]

def assure_tree(key):
	if not key in forrest:
		forrest[key] = empty_lsys()
		print("Created L-Sys with Key: " + key)

def parse_forrest(string):
	systems = string.strip().split("#")
	for system in systems:
		pair = system.strip().split("@")
		key = pair[0]
		rules = pair[1]
		assure_tree(key)
		parse_lsys(forrest[key], rules)

def parse_lsys(lsys, string):
	rules = string.strip().split(",")
	for rule in rules:
		pair = rule.split(".")
		# axiom
		if pair[0] == "*":
			if pair[1] == "0":
				reset_lsys(tree)
			else:
				lsys["axiom"] = pair[1]
		else:
			rules_list = list(filter(lambda x: x[0] != pair[0], lsys["rules"]))
			lsys_rules = [pair]
			lsys_rules.extend(rules_list)
			lsys["rules"] = lsys_rules

def serialize_lsys(lsys):
	ret = ["*." + lsys["axiom"]]
	ret_list = lsys["rules"].copy()
	ret_list.reverse()
	ret.extend(map(lambda x: x[0] + "." + x[1], ret_list))
	return ",".join(ret)

def serialize_forrest():
	ret = map(lambda x: x + "@" + serialize_lsys(forrest[x]), forrest.keys())
	return "#".join(ret)

def load_forrest():
	if os.path.isfile(STATE_FILE):
		with open(STATE_FILE, "r", encoding="utf-8") as file:
			parse_forrest(file.read())
			print("Loaded Forrest: " + serialize_forrest())
	else:
		reset_forrest()
load_forrest()

def store_forrest():
	with open(STATE_FILE, 'w', encoding='utf-8') as file:
		file.write(serialize_forrest())

def print_consumers_count():
	ret = ""
	for key in consumers.keys():
		ret = ret + "/ " + key + ": " + len(consumers[key]) + " /"
	print(ret)

def register_consumer(consumers_cat, websocket):
	consumers_cat.add(websocket)
	print_consumer_count()

def unregister_consumer(websocket):
	for consumers_cat in consumers:
		if websocket in consumers_cat:
			consumers_cat.remove(websocket)
	print_consumer_count()

async def send_lsys(websocket, msg):
	print(websocket)
	print(msg)
	await websocket.send(msg)

async def broadcast(consumers, msg):
	await asyncio.wait([websocket.send(msg) for websocket in consumers])


async def ckar(websocket, path):
	print(path)
	if path == "/ckar_consume":
		await send_lsys(websocket, json.dumps({"type": "lsys", "payload": serialize_lsys()}))
		register(consumers["basic"], websocket)
		try:
			async for message in websocket:
				msg = json.loads(message)
				if msg["type"] == "subscribe" and msg["payload"] == "console":
					register(consumers["console"], websocket)
				if msg["type"] == "subscribe" and msg["payload"] == "view":
					register(consumers["view"], websocket)
		except websockets.exceptions.ConnectionClosed:
			pass
		finally:
			await unregister(websocket)

	if path == "/ckar_serve":
		try:
			print("Connected Server!")
			async for message in websocket:
				print("IN: " + message)
				msg = json.loads(message)
				if msg["type"] == "console" and len(consumers["console"]) > 0:
					await broadcast(consumers["console"], json.dumps({"type": "console", "payload": msg["payload"]}))
				if msg["type"] == "view":
					assure_tree(msg["payload"])
					if len(consumers["view"]) > 0:
						await broadcast(consumers["view"], json.dumps({"type": "view", "payload": msg["payload"]}))
				if msg["type"] == "lsys":
					try:
						parse_forrest(msg["payload"])
						store_forrest()
						if len(consumers["basic"]) > 0:
							await broadcast(consumers["basic"], {"type": "lsys", "payload": serialize_forrest()})
					except Exception as e:
						print("Invalid L-Sys!")
						if len(consumers["console"]) > 0:
							await broadcast(consumers["console"], {"type": "lsys", "payload": "Invalid L-Sys!"})
		except websockets.exceptions.ConnectionClosed:
			pass
		finally:
			print("Disconnected Server!")

start_server = websockets.serve(ckar, HOST, PORT)
asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()