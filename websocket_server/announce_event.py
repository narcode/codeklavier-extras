from netstuff import *
import json

# to select which channel the information is sent to put
# put the according master-credentials.json file into
# the folder.

set_channel_status(json.dumps({
	"visible": True,
	"name": "Live",
	"name_nl": "Live",
	# "status": "offline",
	"description": "No ARquatic events are planned for the next months. Why not book us?",
	"description_nl": "Er zijn de komende maanden geen ARquatic-evenementen gepland. Waarom boekt u ons niet?",
	"eventISODate": "",
	"eventURL": "https://codeklavier.space/arquatic"
}))

# relevant info keys:
# - status (string, "online" or "offline") - can also be "bundled"
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
# - --> note: should be in UTC timezone
# - nightMode (True or False; if True light estimation is deactivated)
# - bundledID 

# if the _nl entries are empty then then the english version will be taken

# set eventISODate and eventURL to "" to 'unannounce'
# one could also set "name" to change the channel name