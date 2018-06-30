#!/usr/bin/env python2
# -*- coding: utf-8 -*-

"""
mqtt-signalbox.py (Python 2)

Simple MQTT subscriber for StudioDisplay and controller for a SignalBox.

This needs to run on the PC where the SignalBox is connected via USB.

Has a MQTT command interface to control the extra 230V outlet:
signalbox/1/command/switch (on, off)

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
import threading
import re
import paho.mqtt.client as paho
import time
import logging
import socket
import os
import ConfigParser # Py2: ConfigParser; Py3: configparser

import signalbox

# Component config from configuration file
config = ConfigParser.SafeConfigParser()
# configfiles are named like "../config/hostname.cfg"
configfile = os.path.dirname(os.path.realpath(__file__)) + '/../config/' + socket.gethostname() + '.cfg'
config.read(configfile)
# define config sections to read
my_section = 'signalbox'
mqtt_section = 'mqtt'


# Log to STDOUT
logger = logging.getLogger(my_section) # name it like my_section
logger.setLevel(logging.INFO)
consoleHandler = logging.StreamHandler()
logger.addHandler(consoleHandler)

logger.info('Read configuration from ' + configfile)

# prepare a lock for thread-safe changing of global variables
lock = threading.Lock()


# Create the callbacks for Mosquitto
def on_connect(self, mosq, obj, rc):
    # show readable connection result (rc)
    logger.info(paho.connack_string(rc))
    if rc == 0:
        # connection successful
        logger.info("Connected to broker " + config.get(mqtt_section, 'host') + ":" + config.get(mqtt_section, 'port') + " as user '" + config.get(mqtt_section, 'username') + "'")

        # Subscribe to device topics
        subscribe_topic = config.get(mqtt_section, 'base_topic') + config.get(my_section, 'subscribe_topic') + '#'
        logger.info("Subscribing to device at " + subscribe_topic)
        mqttclient.subscribe(subscribe_topic)
        set_topic = config.get(mqtt_section, 'base_topic') + config.get(my_section, 'client_topic') + 'set/#'
        logger.info("Subscribing to device config at " + set_topic)
        mqttclient.subscribe(set_topic)
        # Publish connected status
        connected_topic = config.get(mqtt_section, 'base_topic') + config.get(my_section, 'client_topic') + 'connected'
        mqttclient.publish(connected_topic, 2, qos=2, retain=True)
        # show we are connected by turning the WHITE lamp on
        signalbox.handle_token('white', 'on')

def on_disconnect(self, mosq, rc):
    # show we are not connected by turning the WHITE lamp off
    signalbox.handle_token('white', 'off')


def on_subscribe(mosq, obj, mid, granted_qos):
    logger.info("Subscribed with message ID " + str(mid) + " and QOS " + str(granted_qos) + " acknowledged by broker")


def on_message(mosq, obj, msg):
    # msg.payload is a byte string, need to decode it. Assume UTF-8.
    msg.payload = msg.payload.decode('utf-8')
    logger.info("Received message: " + msg.topic + ":" + msg.payload)
    set_topic = config.get(mqtt_section, 'base_topic') + config.get(my_section, 'client_topic') + 'set/'
    subscribe_topic = config.get(mqtt_section, 'base_topic') + config.get(my_section, 'subscribe_topic')
    if msg.topic.startswith(set_topic):
        configitem = msg.topic.split('/')[-1]
        if config.has_option(my_section, configitem):
            # TODO unset when value set to ""
            logger.info("Setting configuration " + configitem + " to " + msg.payload)
            config.set(my_section, configitem, msg.payload)
            if configitem == 'switch':
                # for safety reasons, don’t allow a 230V device to be flashed/blinked
                if msg.payload in ['on', 'off']:
                    signalbox.handle_token(configitem, msg.payload)
        else:
            logger.info("Ignoring unknown configuration item " + configitem)
    elif msg.topic.startswith(subscribe_topic):
        item = msg.topic.split('/')[-1]
        signalbox.handle_token(item, msg.payload)


def on_publish(mosq, obj, mid):
    # logger.info("Published message with message ID: "+str(mid))
    pass


# Create the Mosquitto client
mqttclient = paho.Client(client_id=config.get(my_section, 'client_id'))

# Bind the Mosquitte events to our event handlers
mqttclient.on_connect = on_connect
mqttclient.on_disconnect = on_disconnect
mqttclient.on_subscribe = on_subscribe
mqttclient.on_message = on_message
mqttclient.on_publish = on_publish


# Set the last will, connect to broker, publish connected
connected_topic = config.get(mqtt_section, 'base_topic') + config.get(my_section, 'client_topic') + 'connected'
logger.info("Connecting to broker " + config.get(mqtt_section, 'host') + ":" + config.get(mqtt_section, 'port'))
if config.get(mqtt_section, 'username'):
    mqttclient.username_pw_set(config.get(mqtt_section, 'username'), password=config.get(mqtt_section, 'password'))
mqttclient.will_set(connected_topic, 0, qos=2, retain=True)
mqttclient.connect(config.get(mqtt_section, 'host'), config.getint(mqtt_section, 'port'), 60)
mqttclient.publish(connected_topic, 1, qos=1, retain=True)
# Start the Mosquitto loop in a non-blocking way (uses threading)
mqttclient.loop_start()

time.sleep(2)

# signabox stuff
signalbox.run()

# rc = 0
#
# while rc == 0:
#     pass
