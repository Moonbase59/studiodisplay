#!/usr/bin/env bash

# startall.sh -- start all needed python scripts for StudioDisplay
# Moonbase 2018

DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
echo Changing to $DIR …
cd "$DIR"

x-terminal-emulator -e python/mqtt-callmonitor-fritz.py
x-terminal-emulator -e python/mqtt-idjc.py
x-terminal-emulator -e python/mqtt-radio.py
x-terminal-emulator -e python/mqtt-weather-wunderground.py
x-terminal-emulator -e python/mqtt-astronomy.py
x-terminal-emulator -e python/mqtt-signalbox.py
#x-terminal-emulator -e python/mqtt-signalpi.py
x-terminal-emulator -e python3 -m http.server 8082

firefox -new-window http://$HOSTNAME:8082/
