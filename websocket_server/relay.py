import asyncio
import websockets
import json
import argparse
import sys
import socket

from netstuff import *

# TODO: Refactor into 2 Threads + Thread Safe Queue

# argparse
# https://docs.python.org/2/library/argparse.html

parser = argparse.ArgumentParser(description='Relay for CodeklaviAR')

parser.add_argument('--from',
	help="specify from where to to receive messages",
	action="store",
	dest="from",
	default="MASTER"
)

parser.add_argument('--to',
	help="specify to where to relay messages",
	action="store",
	dest="to",
	default="NONE"
)

parser.add_argument('--from-local',
	help="receive messages from local machine on port " + str(get_default_port()),
	action="store_const",
	const= get_local_websocket_uri("ckar_consume"),
	dest="from"
)

parser.add_argument('--to-master',
	help="relay messages to master server",
	action="store_const",
	const="MASTER",
	dest="to"
)

to_websocket = None

args = vars(parser.parse_args())

if args["to"] == "MASTER":
	args["to"] = get_websocket_uri("ckar_serve")

if args["from"] == "MASTER":
	args["from"] = get_websocket_uri("ckar_consume")

# print(args)

async def repl():
    async with websockets.connect(args["from"]) as websocket:
    	
    	to_websocket = None

    	if args["to"] != "NONE":
    		to_websocket = await websockets.connect(args["to"])

    	async for message in websocket:
    		print(message)
    		if to_websocket != None:
    			# don't relay master transform
    			if not "\"tree\": \"master\"" in message: # hack hack hack
    				await to_websocket.send(message)

print("Relaying from: " + args["from"])
if args["to"] != "NONE":
	print("Relaying to: " + args["to"])

asyncio.get_event_loop().run_until_complete(repl())
asyncio.get_event_loop().run_forever()