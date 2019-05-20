#!/usr/bin/env python3

# TODO: Here we can also check for invalid lsys messages

import asyncio
import websockets
import json
import socket
import os

from netstuff import *

STATE_FILE = "lsys-state.txt"
MASTER_TRANSFORM_FILE = "master-transform.json"

PORT = 8081
HOST = None
DO_ANNOUNCE = True



if HOST == None:
	s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	s.connect(("8.8.8.8", 80))
	HOST = s.getsockname()[0]
	s.close()

if DO_ANNOUNCE:
	announce_server(HOST, PORT)


consumer_categories = ["basic", "console", "view"]
consumers = {}
for category in consumer_categories:
	consumers[category] = set()

forrest = {}


def identity_transform():
	return {"position": [0, 0, 0], "scale": [1, 1, 1], "rotation": [0, 0, 0]}

def load_master_transform():
	with open(MASTER_TRANSFORM_FILE, "r", encoding="utf-8") as file:
		mt = json.loads(file.read())
		return json.dumps({"type": "transform", "tree": "master", "position": mt["position"], "scale": mt["scale"], "rotation": mt["rotation"]})
master_transform_msg = load_master_transform()

def empty_lsys():
	return {"axiom": "0", "rules": [], "transform": identity_transform()}

def reset_forrest():
	global forrest
	forrest = {}
	forrest["1"] = empty_lsys()

def reset_lsys(lsys):
	fresh = empty_lsys()
	lsys["axiom"] = fresh["axiom"]
	lsys["rules"] = fresh["rules"]

def assure_tree(key):
	if not key in forrest:
		forrest[key] = empty_lsys()
		print("Created L-Sys with Key: " + key)

def parse_forrest(string):
	if string == "":
		reset_forrest()
		return

	systems = string.strip().split("#")
	for system in systems:

		pair = system.strip().split("@")
		if len(pair) != 2:
			print("Ignoring invalid tree pair: " + system)
			continue

		key = pair[0]
		rules = pair[1]

		assure_tree(key)
		parse_lsys(forrest[key], rules)

def server_state_msg():
	return json.dumps({"type": "serverState", "numTrees": len(forrest.keys())})

def parse_lsys(lsys, string):
	rules = string.strip().split(",")
	for rule in rules:

		pair = rule.split(".")
		if len(pair) != 2:
			print("Ignoring invalid rule pair: " + rule)
			continue

		# axiom
		if pair[0] == "*":
			if pair[1] == "0":
				reset_lsys(lsys)
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

def load_state():
	if os.path.isfile(STATE_FILE):
		with open(STATE_FILE, "r", encoding="utf-8") as file:
			state = json.loads(file.read())
			parse_forrest(state["forrest"])
			for transform_dict in state["transforms"]:
				forrest[transform_dict["key"]]["transform"] = transform_dict["transform"]
				print(json.dumps(transform_dict))
			print("Loaded Forrest: " + serialize_forrest())
	else:
		reset_forrest()
load_state()

def store_state():
	with open(STATE_FILE, 'w', encoding='utf-8') as file:
		state = {
			"forrest": serialize_forrest(),
			"transforms": list(map(lambda x: {"key": x, "transform": forrest[x]["transform"]}, forrest.keys()))
		}
		file.write(json.dumps(state))

def print_consumers_count():
	ret = ""
	for key in consumers.keys():
		ret = ret + "/ " + key + ": " + str(len(consumers[key])) + " /"
	print(ret)

def register(consumers_cat, websocket):
	consumers_cat.add(websocket)
	print_consumers_count()

def unregister(websocket):
	for key in consumers:
		consumers_cat = consumers[key]
		if websocket in consumers_cat:
			consumers_cat.remove(websocket)
	print_consumers_count()

def apply_transform(msg):
	assure_tree(msg["tree"])
	forrest[msg["tree"]]["transform"] = {"position": msg["position"], "scale": msg["scale"], "rotation": msg["rotation"]}

async def send_msg(websocket, msg):
	await websocket.send(msg)

async def broadcast(consumers, msg):
	await asyncio.wait([websocket.send(msg) for websocket in consumers])


async def ckar(websocket, path):
	print(path)
	if path == "/ckar_consume":
		register(consumers["basic"], websocket)
		await send_msg(websocket, json.dumps({"type": "lsys", "payload": serialize_forrest()}))
		await send_msg(websocket, master_transform_msg)
		for key in forrest.keys():
			transform = forrest[key]["transform"]
			await send_msg(websocket, json.dumps({"type": "transform", "tree": key, "position": transform["position"], "scale": transform["scale"], "rotation": transform["rotation"]}))
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
			unregister(websocket)

	if path == "/ckar_serve":
		try:
			print("Connected Server!")
			await send_msg(websocket, server_state_msg())
			print("Sent Server State: " + server_state_msg())
			async for message in websocket:
				print("IN: " + message)
				msg = json.loads(message)
				if msg["type"] == "console" and len(consumers["console"]) > 0:
					await broadcast(consumers["console"], json.dumps({"type": "console", "payload": msg["payload"]}))
				if msg["type"] == "view":
					assure_tree(msg["payload"])
					if len(consumers["view"]) > 0:
						await broadcast(consumers["view"], json.dumps({"type": "view", "payload": msg["payload"]}))
				if msg["type"] == "transform":
					apply_transform(msg)
					await broadcast(consumers["basic"], json.dumps(msg))
				if msg["type"] == "lsys":
					try:
						parse_forrest(msg["payload"])
						store_state()
						if len(consumers["basic"]) > 0:
							await broadcast(consumers["basic"], json.dumps({"type": "lsys", "payload": serialize_forrest()}))
					except Exception as e:
						print("Invalid L-Sys!")
						print(serialize_forrest())
						print(e);
						if len(consumers["console"]) > 0:
							await broadcast(consumers["console"], json.dumps({"type": "lsys", "payload": "Invalid L-Sys!"}))
		except websockets.exceptions.ConnectionClosed:
			pass
		finally:
			print("Disconnected Server!")

start_server = websockets.serve(ckar, HOST, PORT)
asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
