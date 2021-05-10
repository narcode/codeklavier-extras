#!/usr/bin/env python3

# TODO: Here we can also check for invalid lsys messages

import asyncio
import websockets
import json
import socket
import os
import argparse
import datetime

from netstuff import *

# argparse
# https://docs.python.org/2/library/argparse.html

parser = argparse.ArgumentParser(description='Websocket server for CodeklaviAR')

parser.add_argument('-l', '--local',
	help="don't announce this server to the master server.",
	dest="local",
	action="store_true"
)

parser.add_argument('-d', '--debug',
	help="post exceptions on disconnects",
	dest="debug",
	action="store_true"
)

parser.add_argument('-i', '--ip',
	help="specify the servers ip",
	action="store",
	dest="host",
	default="NONE"
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
	help="explicitly specify a url to announce in the master server",
	action="store",
	dest="url",
	default="NONE"
)

parser.add_argument("-f", "--file",
	help="load state from file",
	action="store",
	dest="file",
	default="NONE"
)

parser.add_argument("--log", 
	help="write all incoming messages to a log file",
	dest="log",
	action="store_true"
)

parser.add_argument("-o", "--output", 
	help="explicitly specify the log file (default: log.txt)",
	action="store",
	dest="logfile",
	default="log.txt"
)

args = vars(parser.parse_args())
# print(args)

STATE_FILE = "lsys-state.json"
LOG_FILE = args["logfile"]
STATE_LOAD_FILE = STATE_FILE

if args["reset"] and (not args["nosave"]) and os.path.exists(STATE_FILE):
	os.remove(STATE_FILE)

if args["reset"] and os.path.exists(LOG_FILE):
	os.remove(LOG_FILE)

PORT = args["port"]
HOST = None
ANNOUNCE_URL = None
DO_ANNOUNCE = not args["local"]

if args["url"] != "NONE":
	ANNOUNCE_URL = args["url"]

if args["file"] != "NONE":
	STATE_LOAD_FILE = args["file"]

if args["host"] != "NONE":
	HOST = args["host"]

NUM_SHAPES = 7

if HOST == None:
	HOST = get_local_ip()

if DO_ANNOUNCE:
	if ANNOUNCE_URL != None:
		announce_server_url(ANNOUNCE_URL)
	elif HOST != None:
		announce_server(HOST, PORT)
else:
	print("Did not announce myself to master server.")

auth_token_server = get_auth_token_server()

if(auth_token_server == None):
	print("Warning: This server does accept messages from anyone!")

consumer_categories = ["basic", "console", "view"]
consumers = {}
for category in consumer_categories:
	consumers[category] = set()


status = {
	"supplierConnected": False,
	"clientsConnected": 0,
	"totalClientsConnected": 0,
	"totalMessagesSent": 0,
	"totalMessagesReceived": 0,
	"runningSince": str(datetime.datetime.now())
}

forest = {}
values = {}

if args["log"]:
	log_file = open(LOG_FILE, "a+")

def write_log(s):
	if args["log"]:
		s = datetime.datetime.now().isoformat() + " - " + s + "\n"
		log_file.write(s)
		log_file.flush()

def identity_transform():
	return {"position": [0, 0, 0], "scale": [1, 1, 1], "rotation": [0, 0, 0]}

def empty_lsys():
	return {"axiom": "0", "rules": [], "transform": identity_transform(), "shape": "1"}

def reset_forest():
	global forest
	global values
	forest = {}
	values = {}
	forest["1"] = empty_lsys()

def reset_lsys(lsys):
	fresh = empty_lsys()
	lsys["axiom"] = fresh["axiom"]
	lsys["rules"] = fresh["rules"]

def assure_tree(key):
	if not key in forest:
		forest[key] = empty_lsys()
		print("Created L-Sys with Key: " + key)

def validate_lsys(string):
	# TODO: implement properly
	return "@" in string and "." in string

def parse_forest(string):
	if string == "":
		reset_forest()
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
		parse_lsys(forest[key], rules)

def server_state_msg():
	return json.dumps({"type": "serverState", "numTrees": len(forest.keys()), "numShapes": NUM_SHAPES})

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

def serialize_forest():
	ret = map(lambda x: x + "@" + serialize_lsys(forest[x]), forest.keys())
	return "#".join(ret)

def load_state(filename):
	if os.path.isfile(filename) and (not args["reset"]):
		with open(filename, "r", encoding="utf-8") as file:
			state = json.loads(file.read())

			# fix old states - can be removed at some point
			if "forrest" in state:
				state["forest"] = state["forrest"]

			parse_forest(state["forest"])
			for transform_dict in state["transforms"]:
				forest[transform_dict["tree"]]["transform"] = transform_dict["transform"]
			for shape_dict in state["shapes"]:
				forest[shape_dict["tree"]]["shape"] = shape_dict["shape"]
			print("Loaded Forest: " + serialize_forest())
	else:
		reset_forest()
load_state(STATE_LOAD_FILE)

def store_state():
	if args["nosave"]:
		return
	with open(STATE_FILE, 'w', encoding='utf-8') as file:
		state = {
			"forest": serialize_forest(),
			"transforms": list(map(lambda x: {"tree": x, "transform": forest[x]["transform"]}, forest.keys())),
			"shapes": list(map(lambda x: {"tree": x, "shape": forest[x]["shape"]}, forest.keys()))
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
	if "marker" in msg["tree"] or "master" in msg["tree"]:
		return

	assure_tree(msg["tree"])
	forest[msg["tree"]]["transform"] = {"position": msg["position"], "scale": msg["scale"], "rotation": msg["rotation"]}

def apply_shape(msg):
	if "marker" in msg["tree"] or "master" in msg["tree"]:
		return
	
	assure_tree(msg["tree"])
	forest[msg["tree"]]["shape"] = msg["shape"]

def apply_values(msg):
	keys = msg["key"].split(",")
	for key in keys:
		values[key] = msg["payload"]

async def send_msg(websocket, msg):
	status["totalMessagesSent"] = status["totalMessagesSent"] + 1
	await websocket.send(msg)

async def broadcast(consumers, msg):
	await asyncio.wait([websocket.send(msg) for websocket in consumers])

async def ckar(websocket, path):
	# print(path)

	if path == "/ckar_status":
		try:
			while True:
				status["clientsConnected"] = len(consumers["basic"])
				await send_msg(websocket, json.dumps(status))
				await asyncio.sleep(2)
		except websockets.exceptions.ConnectionClosed as e:
			pass
		finally:
			pass

	if path == "/ckar_consume":
		register(consumers["basic"], websocket)
		status["totalClientsConnected"] = status["totalClientsConnected"] + 1
		
		
		# this message should be renamed at some point (or removed)
		await send_msg(websocket, json.dumps({"type": "serverEvent", "payload": "endMarkerConfig"}))
		
		for key in forest.keys():
			transform = forest[key]["transform"]
			shape = forest[key]["shape"]
			await send_msg(websocket, json.dumps({"type": "transform", "tree": key, "position": transform["position"], "scale": transform["scale"], "rotation": transform["rotation"]}))
			await send_msg(websocket, json.dumps({"type": "shape", "tree": key, "shape": shape}))
		
		for key in values.keys():
			await send_msg(websocket, json.dumps({"type": "value", "key": key, "payload": values[key]}))

		await send_msg(websocket, json.dumps({"type": "lsys", "payload": serialize_forest()}))

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

	auth_token_client = None

	if path == "/ckar_serve":
		try:
			# print("Connected Supplier!")
			status["supplierConnected"] = True

			await send_msg(websocket, server_state_msg())
			# print("Sent Server State: " + server_state_msg())
			async for message in websocket:

				status["totalMessagesReceived"] = status["totalMessagesReceived"] + 1

				msg = json.loads(message)

				if msg["type"] == "auth":
					auth_token_client = msg["token"]
					print("Received auth token ...")
					if auth_token_server == auth_token_client:
						print("... seems legit!")

				if auth_token_server != None and auth_token_server != auth_token_client:
					print("Websocket not authenticated; not accepting messages!")
					continue

				if msg["type"] != "auth":
					print("IN: " + message)
					write_log(message)
				
				if msg["type"] == "reset":
					print("Server Reset")
					reset_forest()

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
					apply_values(msg)
					if len(consumers["basic"]) > 0:
						await broadcast(consumers["basic"], json.dumps(msg))

				if msg["type"] == "lsys":
					try:
						if not validate_lsys(msg["payload"]):
							raise Exception("L-Sys validation failed!")

						parse_forest(msg["payload"])
						store_state()
						if len(consumers["basic"]) > 0:
							await broadcast(consumers["basic"], json.dumps({"type": "lsys", "payload": serialize_forest()}))
					except Exception as e:
						print("Invalid L-Sys!")
						if len(consumers["console"]) > 0:
							await broadcast(consumers["console"], json.dumps({"type": "console", "payload": "Invalid L-Sys!"}))

		except websockets.exceptions.ConnectionClosed as e:
			if args["debug"]:
				print(e)
		finally:
			status["supplierConnected"] = False


write_log("Started with state: " + serialize_forest())

start_server = websockets.serve(ckar, HOST, PORT, ping_interval=3, ping_timeout=60)
asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
