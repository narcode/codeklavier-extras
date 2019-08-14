import urllib.request
import json
import socket

announce_url = "https://keyboardsunite.com/ckar/"
get_url = "https://keyboardsunite.com/ckar/get.php"

def get_default_port():
	return 8081

def announce_server(host, port):
	url = announce_url + "?host=" + str(host) + "&port=" + str(port)
	req = urllib.request.urlopen(url)
	print("Annoucing " + str(host) + ":" + str(port))
	print(req.read().decode("utf-8"))

def get_websocket_uri(path):
	req = urllib.request.urlopen(get_url)
	data = json.loads(req.read().decode("utf-8") )
	return "ws://" + data["host"] + ":" + data["port"] + "/" + path

def get_local_websocket_uri(path):
	return "ws://" + get_local_ip() + ":" + str(get_default_port()) + "/" + path

def get_local_ip():
	s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	s.connect(("8.8.8.8", 80))
	ret = s.getsockname()[0]
	s.close()
	return ret