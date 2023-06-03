import json
import argparse
import datetime


parser = argparse.ArgumentParser(description='Strip verbose messages from already transformed (for Unity) log')


parser.add_argument("-f", "--file",
	help="load log to feed from file",
	action="store",
	dest="in_file",
	default="log.txt"
)

parser.add_argument("-o", "--output", 
	help="explicitly specify the log file (default: transform_log_output.txt)",
	action="store",
	dest="out_file",
	default="transform_log_output.txt"
)


args = vars(parser.parse_args())

# Opening JSON file
f = open(args['in_file'])
data = json.load(f)
outdata = {"data": []}
outlist = outdata["data"]

with open(args["out_file"], "w") as fp:
    for item in data["data"]:
        if not "console" in item["payload"]:
            outlist.append(item)
    json.dump(outdata, fp)

print("Wrote log to " + args["out_file"])