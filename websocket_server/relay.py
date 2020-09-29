import asyncio
import websockets
import json
import argparse
import sys
import socket
import time

from netstuff import *

# argparse
# https://docs.python.org/2/library/argparse.html

parser = argparse.ArgumentParser(description='Relay for CodeklaviAR')

parser.add_argument('--from',
	help="specify from where to to receive messages",
	action="store",
	dest="from",
	default="NONE"
)

parser.add_argument('--to',
	help="specify to where to relay messages",
	action="store",
	dest="to",
	default="NONE"
)

parser.add_argument('--from-channel',
	help="specify from which channel to receive messages",
	action="store",
	dest="from-channel",
	default="NONE"
)

parser.add_argument('--to-channel',
	help="specify to which channel to relay messages",
	action="store",
	dest="to-channel",
	default="NONE"
)

parser.add_argument('--from-local',
	help="receive messages from local machine on port " + str(get_default_port()),
	action="store_const",
	const= get_local_websocket_uri("ckar_consume"),
	dest="from"
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

parser.add_argument("--delay", "-d",
	help="specify a delay in seconds",
	action="store",
	dest="delay",
	default="NONE"
)

args = vars(parser.parse_args())

if args["to-channel"] == "NONE":
	args["to-channel"] = None

if args["from-channel"] == "NONE":
	args["from-channel"] = None

if args["to"] == "NONE":
	args["to"] = get_websocket_uri("ckar_serve", args["to-channel"])

if args["from"] == "NONE":
	args["from"] = get_websocket_uri("ckar_consume", args["from-channel"])

if args["delay"] == "NONE":
	args["delay"] = None
else:
	args["delay"] = float(args["delay"])


auth_token_client = get_auth_token_client()

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
					# clumsily filtering marker transforms
					if not "\"type\": \"transform\", \"tree\": \"marker" in message or "\"type\": \"transform\", \"tree\": \"master" in message or "\"type\": \"serverEvent\"" in message:
						if not args["silent"]:
							print(" < " + message)
						send_time = 0
						if args["delay"] != None:
							send_time = time.time() + args["delay"]
						if relay_queue != None:
							await relay_queue.put([send_time, message])

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

				if auth_token_client != None:
					await websocket.send(json.dumps({"type": "auth", "token": auth_token_client}))

				# oh still an old message from last time?
				if message != None:
					await websocket.send(message)
					print("Resending message:")
					print(" > " + message)
					relay_queue.task_done()

				while True:
					message = await relay_queue.get()
					now = time.time()
					if message[0] > 0 and now < message[0]:
						await asyncio.sleep(message[0] - now)
					await websocket.send(message[1])
					print(" > " + message[1])
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

if args["delay"] != None:
	print("Relay Delay: " + str(args["delay"]) + " seconds")

async def main():
	global relay_queue

	if args["to"] != "NONE":
		relay_queue = asyncio.Queue()
	await asyncio.gather(*tasks)

asyncio.run(main())
