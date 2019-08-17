#!/usr/bin/env python3

# TODO: Here we can also check for invalid lsys messages

import asyncio
import websockets
import json
import socket
import os
import argparse

from netstuff import *

# argparse
# https://docs.python.org/2/library/argparse.html

parser = argparse.ArgumentParser(description='Websocket server for CodeklaviAR')

parser.add_argument('-l', '--local',
	help="don't announce this Websocket server to the master server.",
	dest="local",
	action="store_true"
)

parser.add_argument('-d', '--debug',
	help="post exceptions on disconnects",
	dest="debug",
	action="store_true"
)

parser.add_argument('-p', '--port',
	help="specify the servers port",
	dest="port",
	action="store",
	type=int,
	default=get_default_port()
)

parser.add_argument("-r", "--reset",
	help="reset server state on startup",
	dest="reset",
	action="store_true"
)

parser.add_argument("-n", "--nosave",
	help="dont store the current lsys state",
	dest="nosave",
	action="store_true"
)

parser.add_argument("-a", "--announce",
	help="announce a host/ip to store in the master server",
	action="store",
	dest="host",
	default="NONE"
)

parser.add_argument("-f", "--file",
	help="load state from file",
	action="store",
	dest="file",
	default="NONE"
)

args = vars(parser.parse_args())
# print(args)

STATE_FILE = "lsys-state.json"
STATE_LOAD_FILE = STATE_FILE
MARKER_TRANSFORMS_FILE = "marker-transforms.json"

if args["reset"] and (not args["nosave"]) and os.path.exists(STATE_FILE):
	os.remove(STATE_FILE)

PORT = args["port"]
HOST = None
ANNOUNCE_HOST = None
DO_ANNOUNCE = not args["local"]

if args["host"] != "NONE":
	ANNOUNCE_HOST = args["host"]

if args["file"] != "NONE":
	STATE_LOAD_FILE = args["file"]

NUM_SHAPES = 6

if HOST == None:
	HOST = get_local_ip()

if ANNOUNCE_HOST == None:
	ANNOUNCE_HOST = HOST

if DO_ANNOUNCE:
	announce_server(ANNOUNCE_HOST, PORT)
else:
	print("Did not announce my IP to master server.")

consumer_categories = ["basic", "console", "view"]
consumers = {}
for category in consumer_categories:
	consumers[category] = set()

forrest = {}

def identity_transform():
	return {"position": [0, 0, 0], "scale": [1, 1, 1], "rotation": [0, 0, 0]}

def load_marker_transforms():
	with open(MARKER_TRANSFORMS_FILE, "r", encoding="utf-8") as file:
		msgs = []
		mts = json.loads(file.read())
		for mt in mts:
			msgs.append(json.dumps({"type": "transform", "tree": mt["tree"], "position": mt["position"], "scale": mt["scale"], "rotation": mt["rotation"]}))
		return msgs
marker_transform_msgs = load_marker_transforms()

def empty_lsys():
	return {"axiom": "0", "rules": [], "transform": identity_transform(), "shape": "1"}

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
	return json.dumps({"type": "serverState", "numTrees": len(forrest.keys()), "numShapes": NUM_SHAPES})

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

def load_state(filename):
	if os.path.isfile(filename) and (not args["reset"]):
		with open(filename, "r", encoding="utf-8") as file:
			state = json.loads(file.read())
			parse_forrest(state["forrest"])
			for transform_dict in state["transforms"]:
				forrest[transform_dict["tree"]]["transform"] = transform_dict["transform"]
			for shape_dict in state["shapes"]:
				forrest[shape_dict["tree"]]["shape"] = shape_dict["shape"]
			print("Loaded Forrest: " + serialize_forrest())
	else:
		reset_forrest()
load_state(STATE_LOAD_FILE)

def store_state():
	if args["nosave"]:
		return
	with open(STATE_FILE, 'w', encoding='utf-8') as file:
		state = {
			"forrest": serialize_forrest(),
			"transforms": list(map(lambda x: {"tree": x, "transform": forrest[x]["transform"]}, forrest.keys())),
			"shapes": list(map(lambda x: {"tree": x, "shape": forrest[x]["shape"]}, forrest.keys()))
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

def apply_shape(msg):
	assure_tree(msg["tree"])
	forrest[msg["tree"]]["shape"] = msg["shape"]

async def send_msg(websocket, msg):
	await websocket.send(msg)

async def broadcast(consumers, msg):
	await asyncio.wait([websocket.send(msg) for websocket in consumers])

async def ckar(websocket, path):
	print(path)
	if path == "/ckar_consume":
		register(consumers["basic"], websocket)
		for marker_transform_msg in marker_transform_msgs:
			await send_msg(websocket, marker_transform_msg)
		await send_msg(websocket, json.dumps({"type": "serverEvent", "payload": "endMarkerConfig"}))
		for key in forrest.keys():
			transform = forrest[key]["transform"]
			shape = forrest[key]["shape"]
			await send_msg(websocket, json.dumps({"type": "transform", "tree": key, "position": transform["position"], "scale": transform["scale"], "rotation": transform["rotation"]}))
			await send_msg(websocket, json.dumps({"type": "shape", "tree": key, "shape": shape}))
		await send_msg(websocket, json.dumps({"type": "lsys", "payload": serialize_forrest()}))
		try:
			async for message in websocket:
				msg = json.loads(message)
				if msg["type"] == "subscribe" and msg["payload"] == "console":
					register(consumers["console"], websocket)
				if msg["type"] == "subscribe" and msg["payload"] == "view":
					register(consumers["view"], websocket)
		except websockets.exceptions.ConnectionClosed as e:
			if args["debug"]:
				print(e)
		finally:
			unregister(websocket)

	if path == "/ckar_serve":
		try:
			print("Connected Supplier!")
			await send_msg(websocket, server_state_msg())
			print("Sent Server State: " + server_state_msg())
			async for message in websocket:
				print("IN: " + message)
				msg = json.loads(message)

				if msg["type"] == "console" and len(consumers["console"]) > 0:
					await broadcast(consumers["console"], json.dumps({"type": "console", "payload": msg["payload"]}))

				if msg["type"] == "consoleStatus" and len(consumers["console"]) > 0:
					await broadcast(consumers["console"], json.dumps({"type": "consoleStatus", "payload": msg["payload"]}))

				if msg["type"] == "view":
					assure_tree(msg["payload"])
					if len(consumers["view"]) > 0:
						await broadcast(consumers["view"], json.dumps({"type": "view", "payload": msg["payload"]}))

				if msg["type"] == "transform":
					apply_transform(msg)
					if len(consumers["basic"]) > 0:
						await broadcast(consumers["basic"], json.dumps(msg))

				if msg["type"] == "shape":
					apply_shape(msg)
					if len(consumers["basic"]) > 0:
						await broadcast(consumers["basic"], json.dumps(msg))

				if msg["type"] == "value":
					#  TODO: apply values
					if len(consumers["basic"]) > 0:
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

		except websockets.exceptions.ConnectionClosed as e:
			if args["debug"]:
				print(e)
		finally:
			print("Disconnected Supplier!")

start_server = websockets.serve(ckar, HOST, PORT, ping_interval=3, ping_timeout=60)
asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
