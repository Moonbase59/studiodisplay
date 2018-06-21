#!/usr/bin/env python2
# -*- coding: utf-8 -*-

"""
mqtt-callmonitor-fritz.py (Python 2)

Simple MQTT publisher for AVM Fritz!Box call monitoring.
You need to enable the call monitor feature on your Fritz!Box
by calling #96*5* from an internal phone once before using this.
(You can disable the feature again with a call to #96*4* any time.)

Publishes caller info for a selected phone number (incoming),
and controls the "BLUE lamp" on a connected Studio Display or signal tower.

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

from call_monitor import callmonitor


# Component config from configuration file
config = ConfigParser.SafeConfigParser()
# configfiles are named like "../config/hostname.cfg"
configfile = os.path.dirname(os.path.realpath(__file__)) + '/../config/' + socket.gethostname() + '.cfg'
config.read(configfile)
# define config sections to read
my_section = 'callmonitor-fritz'
mqtt_section = 'mqtt'


# globals for current state
current = {}
current['phonenumbers'] = []

# Log to STDOUT
logger = logging.getLogger(my_section) # name it like my_section
logger.setLevel(logging.INFO)
consoleHandler = logging.StreamHandler()
logger.addHandler(consoleHandler)

logger.info('Read configuration from ' + configfile)

# read common translation file (no extra gettext here)
i18n_file = os.path.dirname(os.path.realpath(__file__)) + '/../config/lang-' + config.get(my_section, 'locale') + '.json'
i18n = {}
with open(i18n_file) as json_data:
    i18n = json.load(json_data)

logger.info('Read translations from ' + i18n_file)

# helper function (like super-simple gettext)
def _(text):
    translated = text
    try:
        translated = i18n[text]
    except KeyError:
        pass
    return translated

# prepare a lock for thread-safe changing of global variables
lock = threading.Lock()


# Create the callbacks for Mosquitto
def on_connect(self, mosq, obj, rc):
    if rc == 0:
        logger.info("Connected to broker " + config.get(mqtt_section, 'host') + ":" + config.get(mqtt_section, 'port'))

        # Subscribe to device config
        set_topic = config.get(mqtt_section, 'base_topic') + config.get(my_section, 'client_topic') + 'set/#'
        logger.info("Subscribing to device config at " + set_topic)
        mqttclient.subscribe(set_topic)
        # Publish connected status
        connected_topic = config.get(mqtt_section, 'base_topic') + config.get(my_section, 'client_topic') + 'connected'
        mqttclient.publish(connected_topic, 2, qos=2, retain=True)


def on_subscribe(mosq, obj, mid, granted_qos):
    logger.info("Subscribed with message ID " + str(mid) + " and QOS " + str(granted_qos) + " acknowledged by broker")


def on_message(mosq, obj, msg):
    # msg.payload is a byte string, need to decode it. Assume UTF-8.
    msg.payload = msg.payload.decode('utf-8')
    logger.info("Received message: " + msg.topic + ":" + msg.payload)
    set_topic = config.get(mqtt_section, 'base_topic') + config.get(my_section, 'client_topic') + 'set/'
    if msg.topic.startswith(set_topic):
        configitem = msg.topic.split('/')[-1]
        if config.has_option(my_section, configitem):
            # TODO unset when value set to ""
            logger.info("Setting configuration " + configitem + " to " + msg.payload)
            config.set(my_section, configitem, msg.payload)
            if configitem == 'phonenumbers':
                update_phonenumbers()
        else:
            logger.info("Ignoring unknown configuration item " + configitem)


def on_publish(mosq, obj, mid):
    # logger.info("Published message with message ID: "+str(mid))
    pass


# The call monitor’s callback handler
def callmonitor_handler(self, id, action, details):
    # simplified check becaus otherwise we’d have to keep a list of call ids
    check = False
    try:
        if details['to'] in current['phonenumbers'] or details['from'] in current['phonenumbers']:
            check = True
    except KeyError:
        pass

    status_topic = config.get(mqtt_section, 'base_topic') + config.get(my_section, 'client_topic') + 'status/'
    if config.get(my_section, 'publish_topic'):
        status_topic = config.get(mqtt_section, 'base_topic') + config.get(my_section, 'publish_topic')

    if check:
        if action == 'incoming':
            logger.info("Incoming call from " + details['from'] + " to " + details['to'] + " (id=" + str(id) + ")")
            mqttclient.publish(status_topic + "blue", 'flash', retain=True)
            mqttclient.publish(status_topic + "phonenumber", details['from'], retain=True)
            # show a notice on KODI
            if config.getboolean(my_section, 'kodi'):
                kodi_notice = {
                    "title": _(u"Incoming call"),
                    "message": _(u"Incoming call from %(from)s") % { "from": details['from'] }
                }
                mqttclient.publish(config.get(mqtt_section, 'base_topic') + config.get(my_section, 'kodi_command_topic') + "notify", json.dumps(kodi_notice), retain=True)
                logger.info("KODI notification: " + json.dumps(kodi_notice))
        elif action == 'outgoing':
            logger.info("Outgoing call from " + details['from'] + " to " + details['to'] + " (id=" + str(id) + ")")
            mqttclient.publish(status_topic + "blue", 'flash', retain=True)
            mqttclient.publish(status_topic + "phonenumber", details['to'], retain=True)
        elif action == 'accepted':
            logger.info("Connected call from " + details['from'] + " to " + details['to'] + " (id=" + str(id) + ")")
            mqttclient.publish(status_topic + "blue", 'blink', retain=True)
            # show a notice on KODI and pause playback (TV gets timeshifted if so configured)
            if config.getboolean(my_section, 'kodi'):
                kodi_notice = {
                    "title": _(u"Call connected, pausing"),
                    "message": _(u"%(from)s → %(to)s") % { "from": details['from'], "to": details['to'] }
                }
                mqttclient.publish(config.get(mqtt_section, 'base_topic') + config.get(my_section, 'kodi_command_topic') + "notify", json.dumps(kodi_notice), retain=True)
                mqttclient.publish(config.get(mqtt_section, 'base_topic') + config.get(my_section, 'kodi_command_topic') + "playbackstate", 'pause', retain=True)
                logger.info("KODI notification: " + json.dumps(kodi_notice))
                logger.info("Pausing KODI …")
        elif action == 'closed':
            logger.info("Closed call from " + details['from'] + " to " + details['to'] + " (id=" + str(id) + ")")
            mqttclient.publish(status_topic + "blue", 'off', retain=True)
            mqttclient.publish(status_topic + "phonenumber", '', retain=True)
            # show a notice on KODI and pause playback (TV gets timeshifted if so configured)
            if config.getboolean(my_section, 'kodi'):
                kodi_notice = {
                    "title": _(u"Call ended, resuming"),
                    "message": _(u"%(from)s → %(to)s") % { "from": details['from'], "to": details['to'] }
                }
                mqttclient.publish(config.get(mqtt_section, 'base_topic') + config.get(my_section, 'kodi_command_topic') + "notify", json.dumps(kodi_notice), retain=True)
                mqttclient.publish(config.get(mqtt_section, 'base_topic') + config.get(my_section, 'kodi_command_topic') + "playbackstate", 'resume', retain=True)
                logger.info("KODI notification: " + json.dumps(kodi_notice))
                logger.info("Resuming KODI …")
        else:
            pass

# utility funcions
def update_phonenumbers():
    global current
    with lock:
        # phone numbers may be separated by comma, blank, semicolon, dash, colon in config
        current['phonenumbers'] = filter(None, re.split("[, ;\-:]", config.get(my_section, 'phonenumbers')))


# Create the Mosquitto client
mqttclient = paho.Client(client_id=config.get(my_section, 'client_id'))

# Bind the Mosquitte events to our event handlers
mqttclient.on_connect = on_connect
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

# callmonitor stuff
update_phonenumbers()
if config.getboolean(my_section, 'kodi'):
    logger.info("KODI support is enabled.")
call = callmonitor() #Create new instance of py-fritz-monitor, Optinal parameters: host, port
call.register_callback (callmonitor_handler) #Defines a function which is called if any change is detected, unset with call.register_callback (-1)
fritz_connection = False
while not fritz_connection:
    fritz_connection = call.connect()
    time.sleep(2.0)
call.listen()   # this is blocking, reduces CPU load

# rc = 0
#
# while rc == 0:
#     pass

call(disconnect)
