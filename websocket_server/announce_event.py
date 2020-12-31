from netstuff import *

# set eventISODate and eventURL to "" to 'unannounce'
# one could also set "name" to change the channel name.

set_channel_status('''{
	"description": "...",
	"eventISODate": "2020-12-31T12:58:46+00:00",
	"eventURL": "https://cool.event.org",
}''');