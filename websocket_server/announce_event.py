from netstuff import *
import json

# to select which channel the information is sent to put
# put the according master-credentials.json file into
# the folder.

set_channel_status(json.dumps({
	"visible": True,
	"name": "Live",
	"name_nl": "Live NL",
	# "status": "offline",
	"description": "Currently no ARquatic event is planned for the next months. Why not book us?",
	"description_nl": "NL",
	"eventISODate": "",
	"eventURL": "https://codeklavier.space/arquatic"
}))

# relevant info keys:
# - status (string, "online" or "offline")
# - name (string)
# - description (string)
# - name_nl (string)
# - description_nl (string)
# - websocketBaseURL (don't set manually ...)
# - eventURL (string)
# - visible (True or False as boolean, not as string!!)
# - baseScale (number, 1.0 on default)
# - baseDistance (number, 1.0 on default)
# - brightnessMultiplier (number, 1.0 on default)
# - eventISODate (like: 2021-04-16T18:00:00Z)
# - nightMode (True or False; if True light estimation is deactivated)
# - --> note: should be in UTC timezone

# if the _nl entries are empty then then the english version will be taken

# set eventISODate and eventURL to "" to 'unannounce'
# one could also set "name" to change the channel name