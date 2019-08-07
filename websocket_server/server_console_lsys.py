import asyncio
import websockets
import json
import argparse


from netstuff import *

parser = argparse.ArgumentParser(description='LSystem command console for CodeklaviAR websocket server')

parser.add_argument('-l', '--local',
	help="connect to local websocket server.",
	dest="local",
	action="store_true"
)

args = vars(parser.parse_args())

if args["local"]:
	ws_uri = get_local_websocket_uri("ckar_serve")
else:
	ws_uri = get_websocket_uri("ckar_serve")


async def repl():
    async with websockets.connect(ws_uri, ping_interval=3, ping_timeout=None) as websocket:
    	while True: 
        	cmd = input("Enter CKAR LSystem Command: ")
        	await websocket.send(json.dumps({"type": "lsys", "payload": cmd}))

asyncio.get_event_loop().run_until_complete(repl())