import asyncio
import websockets
import json
import argparse
import sys

from concurrent.futures import ThreadPoolExecutor
from netstuff import *

# https://gist.github.com/delivrance/675a4295ce7dc70f0ce0b164fcdbd798
async def ainput(prompt: str = ""):
    with ThreadPoolExecutor(1, "AsyncInput", lambda x: print(x, end="", flush=True), (prompt,)) as executor:
        return (await asyncio.get_event_loop().run_in_executor(
            executor, sys.stdin.readline
        )).rstrip()


parser = argparse.ArgumentParser(description='JSON command console for CodeklaviAR websocket server')

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
        	cmd = await ainput("Enter CKAR JSON Command: ")
        	await websocket.send(cmd)

asyncio.get_event_loop().run_until_complete(repl())