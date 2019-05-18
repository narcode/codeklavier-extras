import asyncio
import websockets
import json

from netstuff import *

async def repl():
    async with websockets.connect(get_websocket_uri("ckar_serve")) as websocket:
    	while True: 
        	cmd = input("Enter CKAR JSON Command: ")
        	await websocket.send(cmd)

asyncio.get_event_loop().run_until_complete(repl())