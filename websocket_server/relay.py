import asyncio
import websockets
import json
import argparse
import sys
import socket

from netstuff import *

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

parser.add_argument("--forward-all", 
	help="relay all messages (also view and console)",
	dest="forward_all",
	action="store_true"
)

parser.add_argument("--silent", "-s",
	help="don't post messages; this might be invoked for performance reasons",
	dest="silent",
	action="store_true"
)

args = vars(parser.parse_args())

if args["to"] == "MASTER":
	args["to"] = get_websocket_uri("ckar_serve")

if args["from"] == "MASTER":
	args["from"] = get_websocket_uri("ckar_consume")


relay_queue = None

async def receiveLoop():
	while True:
		try:
			async with websockets.connect(args["from"], ping_interval=3, ping_timeout=None) as websocket:
				print("Connected as consumer")

				if args["forward_all"]:
					await websocket.send("{\"type\": \"subscribe\", \"payload\": \"console\"}")
					await websocket.send("{\"type\": \"subscribe\", \"payload\": \"view\"}")

				async for message in websocket:
					if not args["silent"]:
						print(" < " + message)
					if relay_queue != None:
						await relay_queue.put(message)

		except Exception as e:
			print("Exception in consumer loop ...")
			print(e)

		print("... reconnecting 'from'-server!")
		await asyncio.sleep(1)

async def supplierLoop():
	message = None
	while True:
		try:
			async with websockets.connect(args["to"], ping_interval=3, ping_timeout=None) as websocket:
				print("Connected as supplier")

				# oh still an old message from last time?
				if message != None:
					await websocket.send(message)
					print("Resending message:")
					print(" > " + message)
					relay_queue.task_done()

				while True:
					message = await relay_queue.get()
					await websocket.send(message)
					print(" > " + message)
					message = None
					relay_queue.task_done()
		
		except Exception as e:
			print("Exception in supplier loop ...")
			print(e)

		print("... reconnecting 'to'-server!")
		await asyncio.sleep(1)

tasks = [receiveLoop()]

print("Relaying from: " + args["from"])
if args["to"] != "NONE":
	print("Relaying to: " + args["to"])
	tasks.append(supplierLoop())

async def main():
	global relay_queue

	if args["to"] != "NONE":
		relay_queue = asyncio.Queue()
	await asyncio.gather(*tasks)

asyncio.run(main())