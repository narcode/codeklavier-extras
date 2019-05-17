import asyncio
import websockets
import json

async def repl():
    async with websockets.connect('ws://192.168.178.235:8081/ckar_consume') as websocket:
    	async for message in websocket:
    		print(message)

asyncio.get_event_loop().run_until_complete(repl())
asyncio.get_event_loop().run_forever()