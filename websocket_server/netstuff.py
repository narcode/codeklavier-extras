import urllib.request
import json
import socket
import hashlib
import base64
import hmac
import os

SET_URL = "https://ar.codeklavier.space/master/set"
GET_URL = "https://ar.codeklavier.space/master/channel"
MASTER_CREDENTIALS_FILE = "master-credentials.json"

AUTH_TOKEN_SERVER_FILE = "auth_token_server.txt"
AUTH_TOKEN_CLIENT_FILE = "auth_token_client.txt"


def get_default_port():
	return 8081


def get_credentials(credentials):
	if(credentials != None):
		return credentials
	try:
		with open(MASTER_CREDENTIALS_FILE, "r", encoding="utf-8") as file:
			credentials = json.loads(file.read())
			return credentials
	except Exception as e:
		pass

	return None


def set_channel_status(payload, credentials=None):
	credentials = get_credentials(credentials)
	if(credentials == None):
		print("... no credentials to announce server to master. Skipping!")
		return
	
	channel = credentials["channel"]
	secret = credentials["secret"]

	hash = hmac.new(bytes(secret.encode("ascii")), msg=bytes(payload.encode("ascii")), digestmod = hashlib.sha256).hexdigest()
	payload = base64.b64encode(bytes(payload.encode("ascii"))).decode('ascii')

	url = SET_URL + "?id=" + channel + "&payload=" + payload + "&hash=" + hash

	try: 
		req = urllib.request.urlopen(url)
		res = req.read().decode("utf-8")
		if res == "OK":
			print("... success! Announced on channel: " + channel)
		else:
			print("... did not succeed.")
	except Exception as e:
		print(e)
		print("... could not validate with master server. Server is not announced!")

def announce_server_url(url, credentials=None):
	print("Annoucing " + str(url) + " ...")
	set_channel_status('{"status": "online", "websocketBaseURL": "' + url + '"}', credentials)

def announce_server(host, port, credentials=None):
	announce_server_url("ws://" + str(host) + ":" + str(port) + "/", credentials)


def get_websocket_uri(path, channel=None):
	if channel == None:
		credentials = get_credentials(None)
		if credentials == None:
			print("No channel specified.")
			return
		else:
			channel = credentials["channel"]

	url = GET_URL + "?id=" + channel

	req = urllib.request.urlopen(url)
	data = json.loads(req.read().decode("utf-8") )
	return data["websocketBaseURL"] + path

def get_local_websocket_uri(path):
	return "ws://" + get_local_ip() + ":" + str(get_default_port()) + "/" + path

def get_local_ip():
	s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	s.connect(("8.8.8.8", 80))
	ret = s.getsockname()[0]
	s.close()
	return ret

def get_auth_token(filename):
	ret = None
	if(os.path.exists(filename)):
		with open(filename, "r", encoding="utf-8") as file:
			ret = file.read().strip()

	return ret

def get_auth_token_server():
	return get_auth_token(AUTH_TOKEN_SERVER_FILE)

def get_auth_token_client():
	return get_auth_token(AUTH_TOKEN_CLIENT_FILE)