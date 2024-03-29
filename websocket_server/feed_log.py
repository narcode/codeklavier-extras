import asyncio
import websockets
import json
import argparse
import datetime

from netstuff import *

parser = argparse.ArgumentParser(description='Log replay for CodeklaviAR websocket server')

parser.add_argument('-l', '--local',
	help="connect to local websocket server",
	dest="local",
	action="store_true"
)

parser.add_argument('-e', '--endless',
	help="play back log in a loop",
	dest="loop",
	action="store_true"
)

parser.add_argument("-f", "--file",
	help="load log to feed from file",
	action="store",
	dest="file",
	default="replay.txt"
)

parser.add_argument("-t", "--timestretch",
	help="time stretch factor",
	action="store",
	dest="timestretch",
	default="1"
)

parser.add_argument('--to',
    help="specify to where to relay messages",
    action="store",
    dest="to",
    default="NONE"
)

parser.add_argument('--to-channel',
    help="select channel which to connect to.",
    action="store",
    dest="to-channel",
    default="NONE"
)

parser.add_argument("-s", "--silent",
	help="don't post messages; this might be invoked for performance reasons",
	dest="silent",
	action="store_true"
)

parser.add_argument("--reset", "-r",
	help="send a reset message to the receiving server on connect",
	dest="reset",
	action="store_true"
)



args = vars(parser.parse_args())

if args["to-channel"] == "NONE":
    args["to-channel"] = None

if args["to"] == "NONE":
    args["to"] = get_websocket_uri("ckar_serve", args["to-channel"])

if args["local"] == True:
	args["to"] = get_local_websocket_uri("ckar_serve")

ws_uri = args["to"]


ts = float(args["timestretch"])

doLoop = args["loop"]

deltaMsgs =  []
with open(args["file"]) as fp:
	lines = fp.readlines()
	before = None
	for line in lines:
		parts = line.split(" - ")
		if parts[1][0] == "{":
			date =  datetime.datetime.strptime(parts[0], "%Y-%m-%dT%H:%M:%S.%f")
			jsonData = parts[1].strip()
			
			if before == None:
				delta = 0
			else:
				delta = (date - before).total_seconds()
			
			before = date
			deltaMsgs.append([delta, jsonData])


def absoluteTimes(deltaMsgs):
	msgs = []
	start = datetime.datetime.now().timestamp()
	now = start

	for msg in deltaMsgs:
		now = now + msg[0] * ts
		msgs.append([now, msg[1]])

	return msgs


auth_token_client = get_auth_token_client()

async def feed():
	async with websockets.connect(ws_uri, ping_interval=3, ping_timeout=None) as websocket:
		continueLooping = True

		if auth_token_client != None:
			await websocket.send(json.dumps({"type": "auth", "token": auth_token_client}))

		if args["reset"]:
			await websocket.send(json.dumps({"type": "reset"}))

		while continueLooping:

			msgs = absoluteTimes(deltaMsgs)

			for msg in msgs:

				now = datetime.datetime.now().timestamp()
				if now < msg[0]:
					delta = msg[0] - now
					await asyncio.sleep(delta)

				if not args["silent"]:
					print(msg[1])
				
				await websocket.send(msg[1])

			if not doLoop:
				continueLooping = False

asyncio.get_event_loop().run_until_complete(feed())
