#!/usr/bin/env python2
# -*- coding: utf-8 -*-

"""
signaltest.py

Simple MQTT publisher to test all signals.
Can be used with SignalBox, SignalPi, and StudioDisplay.

Copyright © 2018 Matthias C. Hormann (@Moonbase59, mhormann@gmx.de)
Maintained at: https://github.com/Moonbase59/studiodisplay

This file is part of StudioDisplay.

StudioDisplay is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

StudioDisplay is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with StudioDisplay.  If not, see <http://www.gnu.org/licenses/>.

---

Diese Datei ist Teil von StudioDisplay.

StudioDisplay ist Freie Software: Sie können es unter den Bedingungen
der GNU General Public License, wie von der Free Software Foundation,
Version 3 der Lizenz oder (nach Ihrer Wahl) jeder neueren
veröffentlichten Version, weiter verteilen und/oder modifizieren.

StudioDisplay wird in der Hoffnung, dass es nützlich sein wird, aber
OHNE JEDE GEWÄHRLEISTUNG, bereitgestellt; sogar ohne die implizite
Gewährleistung der MARKTFÄHIGKEIT oder EIGNUNG FÜR EINEN BESTIMMTEN ZWECK.
Siehe die GNU General Public License für weitere Details.

Sie sollten eine Kopie der GNU General Public License zusammen mit diesem
Programm erhalten haben. Wenn nicht, siehe <http://www.gnu.org/licenses/>.
"""


# IMPORTS
import json
import paho.mqtt.client as paho
import time
import logging
import socket
import os
import ConfigParser # Py2: ConfigParser; Py3: configparser
import random

# Component config from configuration file
config = ConfigParser.SafeConfigParser()
# configfiles are named like "../config/hostname.cfg"
configfile = os.path.dirname(os.path.realpath(__file__)) + '/../config/' + socket.gethostname() + '.cfg'
config.read(configfile)
# define config sections to read
mqtt_section = 'mqtt'
my_section = 'signalpi'

# Log to STDOUT
logger = logging.getLogger(my_section)
logger.setLevel(logging.INFO)
consoleHandler = logging.StreamHandler()
logger.addHandler(consoleHandler)

logger.info('Read configuration from ' + configfile)


# Create the callbacks for Mosquitto
def on_connect(self, mosq, obj, rc):
    if rc == 0:
        logger.info("Connected to broker " + config.get(mqtt_section, 'host') + ":" + config.get(mqtt_section, 'port'))


def on_subscribe(mosq, obj, mid, granted_qos):
    logger.info("Subscribed with message ID " + str(mid) + " and QOS " + str(granted_qos) + " acknowledged by broker")


def on_message(mosq, obj, msg):
    pass

def on_publish(mosq, obj, mid):
    # logger.info("Published message with message ID: "+str(mid))
    pass


# testing stuff

LAMPS = ['green', 'yellow', 'red', 'blue', 'door', 'switch', 'uv', 'all']
STATES = ['on', 'flash', 'blink', 'off']
UV_VALUES = [0.0, 3.0, 6.0, 8.0, 11.0]

subscribe_topic = config.get(mqtt_section, 'base_topic') + config.get(my_section, 'subscribe_topic')
uv_topic = config.get(mqtt_section, 'base_topic') + config.get(my_section, 'uv_topic')

def set_lamp(lamp, state):
    logger.info('LAMP: ' + lamp + ', STATE: ' + state)
    mqttclient.publish(subscribe_topic + lamp, state, qos=2, retain=False)

def set_uv_lamp(value):
    logger.info('UV-LAMP: ' + str(value))
    mqttclient.publish(uv_topic, str(value), qos=2, retain=False)


# Create the Mosquitto client
mqttclient = paho.Client()

# Bind the Mosquitte events to our event handlers
mqttclient.on_connect = on_connect
mqttclient.on_subscribe = on_subscribe
mqttclient.on_message = on_message
mqttclient.on_publish = on_publish


# Set the last will, connect to broker, publish connected
logger.info("Connecting to broker " + config.get(mqtt_section, 'host') + ":" + config.get(mqtt_section, 'port'))
# mqttclient.will_set(config.get(my_section, 'publish_topic') + "connected", 0, qos=2, retain=True)
mqttclient.connect(config.get(mqtt_section, 'host'), config.getint(mqtt_section, 'port'), 60)
# mqttclient.publish(config.get(my_section, 'publish_topic') + "connected", 1, qos=1, retain=True)
# Start the Mosquitto loop in a non-blocking way (uses threading)
mqttclient.loop_start()

time.sleep(2)

rc = 0
#
# while rc == 0:
#     pass

# lamp test
logger.info("LAMP TEST (3s)")
set_uv_lamp(0.0)
set_lamp('all', 'on')
time.sleep(3)

set_lamp('all', 'off')

# all lamps in all states
logger.info("ALL LAMPS, ALL STATES (2s each)")
for l in LAMPS:
    for s in STATES:
        set_lamp(l, s)
        time.sleep(2)

# uv lamp, all colors
logger.info("UV INDEX LAMP, ALL COLORS (1s each)")
set_lamp('uv', 'on')
for u in UV_VALUES:
    set_uv_lamp(u)
    time.sleep(1)

# 100 random states, changing every 100ms
logger.info("200 RANDOM STATES (100ms each)")
for n in range(200):
    l = random.choice(LAMPS)
    s = random.choice(STATES)
    set_lamp(l, s)
    time.sleep(0.1)

logger.info("DONE, ALL LAMPS OFF")
# for machines that don’t recognize "all" (like StudioDisplay)
for l in LAMPS:
    set_lamp(l, 'off')
# SignalPis usually have the UV lamp on
set_uv_lamp(0.0)
set_lamp('uv', 'on')

# wait till things settle (we might have been quite fast)
time.sleep(3)
mqttclient.disconnect()
