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


parser = argparse.ArgumentParser(description='LSystem command console for CodeklaviAR websocket server')

parser.add_argument('-l', '--local',
	help="connect to local websocket server.",
	dest="local",
	action="store_true"
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


args = vars(parser.parse_args())

if args["to-channel"] == "NONE":
    args["to-channel"] = None

if args["to"] == "NONE":
    args["to"] = get_websocket_uri("ckar_serve", args["to-channel"])

channel = args["to"]

if args["local"]:
    ws_uri = get_local_websocket_uri("ckar_serve")
else:
    ws_uri = get_websocket_uri("ckar_serve", channel)

auth_token_client = get_auth_token_client()

async def repl():
    async with websockets.connect(ws_uri, ping_interval=3, ping_timeout=None) as websocket:
        if auth_token_client != None:
            await websocket.send(json.dumps({"type": "auth", "token": auth_token_client}))
        while True: 
            cmd = await ainput("Enter CKAR LSystem Command: ")
            await websocket.send(json.dumps({"type": "lsys", "payload": cmd}))

asyncio.get_event_loop().run_until_complete(repl())