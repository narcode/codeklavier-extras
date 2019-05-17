import asyncio
import websockets
import json


async def repl():
    async with websockets.connect('ws://192.168.178.235:8081/ckar_serve') as websocket:
    	while True: 
        	cmd = input("Enter CKAR LSysm Command: ")
        	await websocket.send(json.dumps({"type": "lsys", "payload": cmd}))

asyncio.get_event_loop().run_until_complete(repl())