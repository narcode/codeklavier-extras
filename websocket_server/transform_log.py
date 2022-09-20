import json
import argparse
import datetime


parser = argparse.ArgumentParser(description='Transform log files for playback in Unity')


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

parser.add_argument("-t", "--time-offset",
    help="time offset in seconds",
    action="store",
    dest="time_offset",
    default="0"
)

args = vars(parser.parse_args())

offset = float(args["time_offset"])

msgs =  []
with open(args["in_file"]) as fp:
	lines = fp.readlines()
	start_date = datetime.datetime.strptime(lines[0].split(" - ")[0], "%Y-%m-%dT%H:%M:%S.%f")
	for line in lines:
		parts = line.split(" - ")
		if parts[1][0] == "{":
			date = datetime.datetime.strptime(parts[0], "%Y-%m-%dT%H:%M:%S.%f")
			jsonData = parts[1].strip()
			t = (date - start_date).total_seconds() + offset

			if "\"type\": \"console\"" in jsonData: continue
			
			msgs.append({"time": t, "payload": jsonData})

with open(args["out_file"], "w") as fp: 
    json.dump({"data": msgs}, fp)

print("Wrote log to " + args["out_file"])