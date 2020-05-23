import asyncio
import websockets
import json
import argparse
import datetime

from netstuff import *

parser = argparse.ArgumentParser(description='JSON command console for CodeklaviAR websocket server')

parser.add_argument('-l', '--local',
	help="connect to local websocket server.",
	dest="local",
	action="store_true"
)

parser.add_argument("-f", "--file",
	help="load state from file",
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

args = vars(parser.parse_args())

if args["local"]:
	ws_uri = get_local_websocket_uri("ckar_serve")
else:
	ws_uri = get_websocket_uri("ckar_serve")

ts = float(args["timestretch"])

msgs =  []
with open(args["file"]) as fp:
	lines = fp.readlines()
	before = None
	for line in lines:
		parts = line.split(" - ");
		if parts[1][0] == "{":
			date =  datetime.datetime.strptime(parts[0], "%Y-%m-%dT%H:%M:%S.%f")
			json = parts[1].strip()
			
			if before == None:
				delta = 0
			else:
				delta = (date - before).total_seconds()
			
			before = date
			msgs.append([delta, json]);


async def feed():
    async with websockets.connect(ws_uri, ping_interval=3, ping_timeout=None) as websocket:
    	for msg in msgs:
    		print(msg[1])
    		await websocket.send(msg[1])
    		await asyncio.sleep(msg[0] * ts)

asyncio.get_event_loop().run_until_complete(feed())
