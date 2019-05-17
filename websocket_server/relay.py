import asyncio
import websockets
import json

from netstuff import *

async def repl():
    async with websockets.connect(get_websocket_uri("ckar_consume")) as websocket:
    	async for message in websocket:
    		print(message)

asyncio.get_event_loop().run_until_complete(repl())
asyncio.get_event_loop().run_forever()