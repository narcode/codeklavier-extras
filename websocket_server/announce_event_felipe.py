from netstuff import *
import json

# to select which channel the information is sent to put
# put the according master-credentials.json file into
# the folder.

# set eventISODate and eventURL to "" to 'unannounce'
# one could also set "name" to change the channel name

set_channel_status(json.dumps({
	"description": "anne has an elephant crush",
	"name": "Rehearsals",
	"visible": True,
	"status": "online"
}));

# relevant info keys:
# - status ("online" or "offline")
# - name
# - description
# - websocketBaseURL (don't set manually ...)
# - eventURL
# - eventISODate (like: 2021-04-16T18:00:00Z)
# - --> note: should be in UTC timezone
