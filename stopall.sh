#!/usr/bin/env bash

# stopall.sh -- kill all running python scripts for StudioDisplay
# NO GUARANTEES -- USE WITH CARE!
# Moonbase 2018

# kill everything that looks like "python mqtt-" or "python http.server"
echo "Killing" $(ps aux | egrep '.*[p]ython3? (.*mqtt-.*\.py|.*http\.server.*)' | awk '{print $2}')
kill $(ps aux | egrep '.*[p]ython3? (.*mqtt-.*\.py|.*http\.server.*)' | awk '{print $2}')
