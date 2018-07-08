#!/usr/bin/env python2
# -*- coding: utf-8 -*-

"""
rgbtest.py

Simple MQTT publisher to test all RGB lights.
Can be used with UnicornLight or any light that accepts comma-separated RGB.

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
target_topic = 'bulb/1/rgb/set'

# Log to STDOUT
logger = logging.getLogger(my_section)
logger.setLevel(logging.INFO)
consoleHandler = logging.StreamHandler()
logger.addHandler(consoleHandler)

logger.info('Read configuration from ' + configfile)


# Create the callbacks for Mosquitto
def on_connect(self, mosq, obj, rc):
    if rc == 0:
        # connection successful
        logger.info("Connected to broker " + config.get(mqtt_section, 'host') + ":" + config.get(mqtt_section, 'port') + " as user '" + config.get(mqtt_section, 'username') + "'")


def on_subscribe(mosq, obj, mid, granted_qos):
    logger.info("Subscribed with message ID " + str(mid) + " and QOS " + str(granted_qos) + " acknowledged by broker")


def on_message(mosq, obj, msg):
    pass

def on_publish(mosq, obj, mid):
    # logger.info("Published message with message ID: "+str(mid))
    pass


# testing stuff

target = config.get(mqtt_section, 'base_topic') + target_topic

def set_lamp(r,g,b):
    s = ",".join((str(r), str(g), str(b)))
    logger.info('LAMP: ' + s)
    mqttclient.publish(target, s, qos=2, retain=False)


# Create the Mosquitto client
mqttclient = paho.Client()

# Bind the Mosquitte events to our event handlers
mqttclient.on_connect = on_connect
mqttclient.on_subscribe = on_subscribe
mqttclient.on_message = on_message
mqttclient.on_publish = on_publish


# Set the last will, connect to broker, publish connected
logger.info("Connecting to broker " + config.get(mqtt_section, 'host') + ":" + config.get(mqtt_section, 'port'))
if config.get(mqtt_section, 'username'):
    mqttclient.username_pw_set(config.get(mqtt_section, 'username'), password=config.get(mqtt_section, 'password'))
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

# 100 random states, changing every 100ms
logger.info("1000 RANDOM STATES (100ms each)")
for n in range(1000):
    r = random.randint(0,255)
    g = random.randint(0,255)
    b = random.randint(0,255)
    set_lamp(r,g,b)
    time.sleep(0.1)

# wait till things settle (we might have been quite fast)
time.sleep(3)
mqttclient.disconnect()
