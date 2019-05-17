import urllib.request
import json

announce_url = "https://keyboardsunite.com/ckar/"
get_url = "https://keyboardsunite.com/ckar/get.php"

def announce_server(host, port):
	url = announce_url + "?host=" + str(host) + "&port=" + str(port)
	req = urllib.request.urlopen(url)
	print(req.read().decode("utf-8"))

def get_websocket_uri(path):
	req = urllib.request.urlopen(get_url)
	data = json.loads(req.read().decode("utf-8") )
	return "ws://" + data["host"] + ":" + data["port"] + "/" + path