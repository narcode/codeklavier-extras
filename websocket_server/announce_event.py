from netstuff import *
import json

# to select which channel the information is sent to put
# put the according master-credentials.json file into
# the folder.

# set eventISODate and eventURL to "" to 'unannounce'
# one could also set "name" to change the channel name

set_channel_status(json.dumps({
	"description": "This is channel is usually hidden and top secret, so I wonder if your name might actually be Anne or Felipe?"
}));

# relevant info keys:
# - status ("online" or "offline")
# - name
# - description
# - websocketBaseURL (don't set manually ...)
# - eventURL
# - visible (true or false as boolean, not as string!!)
# - eventISODate (like: 2021-04-16T18:00:00Z)
# - --> note: should be in UTC timezone
