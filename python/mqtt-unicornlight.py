#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
sudo ./mqtt-unicornlight.py (Python 2)

Simple MQTT client for a Pi with a Unicorn HAT/pHAT,
making it a controllable ambient light source.

Color temperature can be controlled in °K or r,g,b.
Brightness can be controlled in 0..100% steps.

Unfortunately, this MUST be started with "sudo",
it’s a Unicorn library requirement. Sigh.
This also means you must have the Python modules available globally,
i.e. having done "sudo pip install paho-mqtt" and so forth.

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


import sys
try:
    import unicornhat as uh
except ImportError:
    exit("Unicornlight requires a Raspberry Pi with Pimoroni's 'unicornhat' installed.\nInstall with: curl -sS https://get.pimoroni.com/unicornhat | bash")

import colortemperature as ct
import time

uh.set_layout(uh.AUTO)
uh.brightness(1.0)


# Some typical characteristic color temperatures:
#    1.500 K -- Kerze
#    1.700 K -- Match flame, low-pressure sodium lamps (LPS/SOX)
#    1.850 K -- Candle flame, sunset/sunrise
#    2.000 K -- Natriumdampflampe (SON-T)
#    2.600 K -- Glühlampe (40 W)
#    2.700 K -- Glühlampe (60 W), "soft white" compact flourescent and LED lamps
#    2.800 K -- Glühlampe (100 W)
#    2.700–2.800 K -- Halogenlampe (230 V, Eco-Halogen, 30–60 W)
#    3.000 K -- Glühlampe (200 W), "warm white" compact flourescent and LED lamps
#    3.000–3.200 K -- Halogenlampe (12 V)
#    3.200 K -- Fotolampe Typ B, Halogenglühlampe
#    3.400 K -- Fotolampe Typ A bzw. S, Spätabendsonne kurz vor Dämmerungsbeginn
#    3.600 K -- Operationssaalbeleuchtung
#    4.000 K -- Leuchtstofflampe (Neutralweiß)
#    4.120 K -- Mondlicht
#    4.500–5.000 K -- Xenonlampe, Lichtbogen
#    5.000 K -- Morgen-/Abendsonne, D50-Normlicht (Druckerei, Weißpunkt für Wide-Gamut- und ColorMatch-RGB)
#    5.500 K -- Vormittags-/Nachmittagssonne
#    5.500–5.600 K -- Elektronenblitzgerät
#    5.500–5.800 K -- Mittagssonne, Bewölkung
#    6.500–7.500 K -- Bedeckter Himmel
#    6.504 K -- D65 Normlicht (Weißpunkt für sRGB, Adobe-RGB und PAL/SECAM-TV)
#    6.500–9.500 K -- LCD or CRT screen
#    7.500–8.500 K -- Nebel, starker Dunst
#    7.510 K -- D75 Normlicht
#    9.000–12.000 K -- Blauer (wolkenloser) Himmel auf der beschatteten Nordseite, Blaue Stunde
#    9.312 K -- D93 Normlicht (Weißpunkt für besondere blaue Leuchtdisplays)
#   15.000–27.000 K -- Klares blaues, nördliches Himmelslicht

import json
# import threading
import re
import paho.mqtt.client as paho
import time
import logging
import socket
import os
import ConfigParser # Py2: ConfigParser; Py3: configparser

# Component config from configuration file
config = ConfigParser.SafeConfigParser()
# configfiles are named like "../config/hostname.cfg"
configfile = os.path.dirname(os.path.realpath(__file__)) + '/../config/' + socket.gethostname() + '.cfg'
config.read(configfile)
# define config sections to read
my_section = 'unicornlight'
mqtt_section = 'mqtt'

# Log to STDOUT
logger = logging.getLogger(my_section) # name it like my_section
logger.setLevel(logging.INFO)
consoleHandler = logging.StreamHandler()
logger.addHandler(consoleHandler)

logger.info('Read configuration from ' + configfile)

# prepare a lock for thread-safe changing of global variables
# lock = threading.Lock()


# Create the callbacks for Mosquitto
def on_connect(self, mosq, obj, rc):
    if rc == 0:
        logger.info("Connected to broker " + config.get(mqtt_section, 'host') + ":" + config.get(mqtt_section, 'port'))

        # Subscribe to device topics
        set_topic = config.get(mqtt_section, 'base_topic') + config.get(my_section, 'client_topic') + 'set/#'
        logger.info("Subscribing to device config at " + set_topic)
        mqttclient.subscribe(set_topic)
        # Publish connected status
        connected_topic = config.get(mqtt_section, 'base_topic') + config.get(my_section, 'client_topic') + 'connected'
        mqttclient.publish(connected_topic, 2, qos=2, retain=True)
        # set LED brightness (0.0 .. 1.0)
        set_brightness(config.get(my_section, 'brightness'))
        set_color(config.get(my_section, 'color'))
        set_power(config.get(my_section, 'power'))
        # Subscribe to a light source topic, if one is given
        light_topic = config.get(mqtt_section, 'base_topic') + config.get(my_section, 'light_topic')
        if light_topic:
            logger.info("Subscribing to light topic at " + light_topic)
            mqttclient.subscribe(light_topic)

def on_disconnect(self, mosq, rc):
    pass

def on_subscribe(mosq, obj, mid, granted_qos):
    logger.info("Subscribed with message ID " + str(mid) + " and QOS " + str(granted_qos) + " acknowledged by broker")

def on_unsubscribe(mosq, obj, mid):
    logger.info("Unsubscribed with message ID " + str(mid) + " acknowledged by broker")


def on_message(mosq, obj, msg):
    # msg.payload is a byte string, need to decode it. Assume UTF-8.
    msg.payload = msg.payload.decode('utf-8')
    logger.info("Received message: " + msg.topic + ":" + msg.payload)
    set_topic = config.get(mqtt_section, 'base_topic') + config.get(my_section, 'client_topic') + 'set/'
    light_topic = config.get(mqtt_section, 'base_topic') + config.get(my_section, 'light_topic')

    if light_topic and msg.topic.startswith(light_topic):
        set_color(msg.payload)

    if msg.topic.startswith(set_topic):
        configitem = msg.topic.split('/')[-1]
        if config.has_option(my_section, configitem):
            # TODO unset when value set to ""
            logger.info("Setting configuration " + configitem + " to " + msg.payload)
            if configitem == 'brightness':
                set_brightness(msg.payload)
            elif configitem == 'color':
                set_color(msg.payload)
            elif configitem == 'power':
                set_power(msg.payload)
            elif configitem == 'light_topic':
                # unsubscribe first, if needed
                if light_topic:
                    logger.info("Unsubscribing from light topic at " + light_topic)
                    mqttclient.unsubscribe(light_topic)
                light_topic = msg.payload
                # if new topic is not empty, subscribe to it
                if light_topic:
                    logger.info("Subscribing to light topic at " + light_topic)
                    mqttclient.subscribe(light_topic)
            config.set(my_section, configitem, msg.payload)
        else:
            logger.info("Ignoring unknown configuration item " + configitem)


def on_publish(mosq, obj, mid):
    # logger.info("Published message with message ID: "+str(mid))
    pass


# UnicornLight/Unicorn (p)HAT stuff

# set "power", pseudo function for smarthome automation
# just set brightness to zero (or last value)
def set_power(value):
    # Possible boolean values in the configuration.
    BOOLEAN_STATES = {'1': True, 'yes': True, 'true': True, 'on': True,
                      '0': False, 'no': False, 'false': False, 'off': False}
    if value.lower() in BOOLEAN_STATES:
        status_topic = config.get(mqtt_section, 'base_topic') + config.get(my_section, 'client_topic') + 'status/power'
        if BOOLEAN_STATES[value.lower()]:
            uh.brightness(config.getfloat(my_section, 'brightness') / 100.0)
            uh.show()
            config.set(my_section, 'power', 'on')
            mqttclient.publish(status_topic, 'on', retain=True)
        else:
            uh.brightness(0.0)
            uh.show()
            config.set(my_section, 'power', 'off')
            mqttclient.publish(status_topic, 'off', retain=True)
            logger.info("Power set to " + config.get(my_section, 'power'))

# set Unicorn LED’s brightness from 0 to 100%
def set_brightness(value):
    try:
        value = int(value)
    except ValueError:
        return  # ignore wrong values
    if value < 0:
        value = 0
    elif value > 100:
        value = 100

    uh.brightness(value / 100.0)
    uh.show()
    config.set(my_section, 'brightness', str(value))
    status_topic = config.get(mqtt_section, 'base_topic') + config.get(my_section, 'client_topic') + 'status/brightness'
    mqttclient.publish(status_topic, config.get(my_section, 'brightness'), retain=True)
    logger.info("Brightness set to " + config.get(my_section, 'brightness'))

# set Unicorn LED’s color, either °K or R,G,B
def set_color(value):
    # color RGB calues may be separated by comma, blank, semicolon, dash, colon in config
    colors = filter(None, re.split("[, ;\-:]", value))
    if len(colors) == 3:
        # RGB values
        for k, v in enumerate(colors):
            try:
                colors[k] = int(v)
            except ValueError:
                colors[k] = 0
            if colors[k] < 0:
                colors[k] = 0
            if colors[k] > 255:
                colors[k] = 255
        r, g, b = colors
    elif len(colors) == 1:
        # value in degrees Kelvin, only good between 1000..40000
        try:
            colors[0] = int(colors[0])
        except ValueError:
            colors[0] = 6504 # D65
        if colors[0] < 1000:
            colors[0] = 1000
        elif colors[0] > 40000:
            colors[0] = 40000
        r, g, b = ct.color_temperature_to_rgb(colors[0])
    else:
        # return early, no valid colors
        logger.info("Ignoring invalid color: " + value)
        return

    uh.set_all(r, g, b)
    uh.show()
    config.set(my_section, 'color', ','.join([str(r), str(g), str(b)]))
    status_topic = config.get(mqtt_section, 'base_topic') + config.get(my_section, 'client_topic') + 'status/color'
    mqttclient.publish(status_topic, config.get(my_section, 'color'), retain=True)
    logger.info("Color set to " + config.get(my_section, 'color'))


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
mqttclient.will_set(connected_topic, 0, qos=2, retain=True)
mqttclient.connect(config.get(mqtt_section, 'host'), config.getint(mqtt_section, 'port'), 60)
mqttclient.publish(connected_topic, 1, qos=1, retain=True)
# Start the Mosquitto loop in a non-blocking way (uses threading)
mqttclient.loop_start()

time.sleep(2)

# UnicornLight stuff

rc = 0

# don’t eat up too many CPU cycles
while rc == 0:
    time.sleep(60)
