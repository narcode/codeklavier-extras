import asyncio
import websockets
import json
import argparse
import random
import math
import time

from netstuff import *

parser = argparse.ArgumentParser(description='stress test for the CodeklaviAR server')

parser.add_argument('-l', '--local',
	help="connect to local websocket server.",
	dest="local",
	action="store_true"
)

parser.add_argument('-s', '--silent',
	help="don't connect as a supplier and send random messages",
	dest="silent",
	action="store_true"
)

parser.add_argument("-n", 
	help="number of simultaneous connections",
	type=int,
	dest="n",
	default=40
)

args = vars(parser.parse_args())

if args["local"]:
	serve_uri = get_local_websocket_uri("ckar_serve")
	consume_uri = get_local_websocket_uri("ckar_consume")
else:
	serve_uri = get_websocket_uri("ckar_serve")
	consume_uri = get_websocket_uri("ckar_consume")

clients = []

def random_lsys():
	return json.dumps({"type": "lsys", "payload": "1@*." + str(int(random.randint(0, 5000)))})

took_time = False
this_time = 0
sent_message = False

async def receive_loop(i):
	global took_time, this_time
	async with websockets.connect(consume_uri) as websocket:
		async for message in websocket:
			clients[i]["payload"] = message
			numAgree = 0

			for client in clients:
				if client["payload"] == message:
					numAgree = numAgree + 1

			perc = math.floor(numAgree / len(clients) * 100)

			if perc == 100:
				if took_time and sent_message:
					print("Delivery complete; took " + str(int(round(time.time() * 1000)) - this_time) + "ms")
				took_time = False
			else:
				if not took_time:
					this_time = int(round(time.time() * 1000))
					took_time = True

			await asyncio.sleep(0.00000001)

async def send_loop():
	global sent_message
	async with websockets.connect(serve_uri) as websocket:
		print("Connecting and passing some time so that all status is served ...")
		await asyncio.sleep(4)
		print("... let's go!")
		while True:
			if not args["silent"]:
				await websocket.send(random_lsys())
			sent_message = True
			await asyncio.sleep(2)


tasks = []

for i in range(args["n"]):
	clients.append({"payload": "init", "id": i})
	tasks.append(receive_loop(i))

tasks.append(send_loop())

async def main():
	await asyncio.gather(*tasks)

asyncio.run(main())