#!/usr/bin/env python3
import asyncio
import os
import argparse
from pythonosc import osc_server
from pythonosc import dispatcher
from pythonosc.udp_client import SimpleUDPClient
from threading import Thread
import json

import aiohttp

#HOST = '192.168.178.178:8081'

parser = argparse.ArgumentParser() 
parser.add_argument('-ip', type=str, help='IP address and port, i.e. 127.0.0.1:8081')
parser.add_argument('-type', type=str, help='boot as OSC client')
args = vars(parser.parse_args())

URL = f'ws://{args["ip"]}/ckar_serve'
CONSUME = 'wss://ar.codeklavier.space/socket/public/ckar_consume'

tree = None 
key = None
val = None

sending = False
opened = False

oscClient = SimpleUDPClient("127.0.0.1", 57120)

def osc():
    def osc_handler(unused_addr, k, t, v):
        global sending, tree, val, key
        tree = t
        val = v 
        key = k
        sending = True

    handler = dispatcher.Dispatcher()
    handler.map("/py", osc_handler)

    server = osc_server.ThreadingOSCUDPServer(("127.0.0.1", 1111), handler)
    server.serve_forever()
    

async def ws_server():
    global sending, opened
    opened = True
    session = aiohttp.ClientSession()
    while opened:
        if sending:
            try:                
                async with session.ws_connect(URL) as ws:
                    await prompt_and_send(ws, tree, key, val)
                    await asyncio.sleep(0) # <-- did the trick to keep the connection alive
            except:
                opened = False 
                print("Websockets serve connection failed. Is the ip and port correct?")
                os._exit(1)
        await asyncio.sleep(0.1)
        
        
async def ws_consume():
    global opened
    session = aiohttp.ClientSession()
    while True:           
        async with session.ws_connect(CONSUME) as ws:
            async for msg in ws:
                d = json.loads(msg.data);
                print(d)
                if d['type'] == 'transform':
                    oscClient.send_message("/public_transform", 1)
            await asyncio.sleep(0) # <-- did the trick to keep the connection alive
        await asyncio.sleep(0.1)
        

async def prompt_and_send(ws, tree, key, val):
    global sending, opened
    msg = {'type': 'value','key': f"{tree}-{key}", 'payload': f"{val}"}
    print(msg)
    sending = False
    try:        
        await ws.send_json(msg)
    except:   
        opened = False
        print("restart websockets")
        loop.run_until_complete(ws_server()) 


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    if args["type"] == 'osc':
        print('booted as websocket consumer and osc sender')
        loop.run_until_complete(ws_consume())
    else:
        print('booted as websocket sender and osc consumer')
        t = Thread(target=osc, name='osc server')
        t.start()        
        loop.run_until_complete(ws_server())    