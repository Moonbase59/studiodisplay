#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
mqtt-radio.py (Python 3)

Simple MQTT publisher of radio stream data using icymonitor.py.
Publishes the current title (plus a timestamp and the station name)

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
import configparser # Py2: ConfigParser; Py3: configparser
import icymonitor


# Component config from configuration file
config = configparser.SafeConfigParser()
# configfiles are named like "../config/hostname.cfg"
configfile = os.path.dirname(os.path.realpath(__file__)) + '/../config/' + socket.gethostname() + '.cfg'
config.read(configfile)
# define config sections to read
my_section = 'radio'
mqtt_section = 'mqtt'


# Log to STDOUT
logger = logging.getLogger(my_section) # name it like my_section
logger.setLevel(logging.INFO)
consoleHandler = logging.StreamHandler()
logger.addHandler(consoleHandler)

logger.info('Read configuration from ' + configfile)


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
        # publish URL and encoding, in case the station delivers no stream metadata
        status_topic = config.get(mqtt_section, 'base_topic') + config.get(my_section, 'client_topic') + 'status/'
        mqttclient.publish(status_topic + "url", config.get(my_section, 'url'), retain=True)
        mqttclient.publish(status_topic + "encoding", config.get(my_section, 'encoding'), retain=True)


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
            # publish URL and encoding, in case the station delivers no stream metadata
            if configitem in ['url', 'encoding']:
                status_topic = config.get(mqtt_section, 'base_topic') + config.get(my_section, 'client_topic') + 'status/' + configitem
                mqttclient.publish(status_topic, msg.payload, retain=True)
            # stop icymonitor in order to reload with new data
            icymonitor.icymonitor_stop()
        else:
            logger.info("Ignoring unknown configuration item " + configitem)

def on_publish(mosq, obj, mid):
    # logger.info("Published message with message ID: "+str(mid))
    pass


# this gets called by icymonitor when the stream title changes
def title_callback(timestamp, station='', genre='', description='', title=''):

    if timestamp:
        timestamp = int(timestamp) # make the float an int (full seconds)

    logger.info(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp)) + ': ' + station + ' - ' + title)

#   Building message info as JSON package
    send_msg = {
        'timestamp': timestamp,
        'url': config.get(my_section, 'url'),
        'encoding': config.get(my_section, 'encoding'),
        'station': station,
        'genre': genre,
        'description': description,
        'title': title
    }

#  Publish data json or single
    status_topic = config.get(mqtt_section, 'base_topic') + config.get(my_section, 'client_topic') + 'status/'
    if config.getboolean(my_section, 'json'):
        mqttclient.publish(status_topic + "json", payload=json.dumps(send_msg), qos=2, retain=True)
        logger.info("Published radio json data to " + status_topic)
    else:
        mqttclient.publish(status_topic + "timestamp", timestamp, retain=True)
        mqttclient.publish(status_topic + "url", config.get(my_section, 'url'), retain=True)
        mqttclient.publish(status_topic + "encoding", config.get(my_section, 'encoding'), retain=True)
        mqttclient.publish(status_topic + "station", station, retain=True)
        mqttclient.publish(status_topic + "genre", genre, retain=True)
        mqttclient.publish(status_topic + "description", description, retain=True)
        mqttclient.publish(status_topic + "title", title, retain=True)
        logger.info("Published " + my_section + " data to " + status_topic)



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

rc = 0

while rc == 0:
    logger.info("Connecting to radio stream at " + config.get(my_section, 'url') + " (encoding="  + config.get(my_section, 'encoding') + ")")
    # icymonitor is blocking!
    # it will return False (0) on normal shutdown, True (1) if an error occurred
    result = icymonitor.icymonitor(config.get(my_section, 'url'), callback=title_callback, encoding=config.get(my_section, 'encoding'), timeout=config.getfloat(my_section, 'timeout'))
    #print("Result={}".format(result))
    if result:
        # Some error has occurred, wait 10s before reconnect
        logger.info("Icymonitor reported an error, waiting " + config.get(my_section, 'retry_wait') + "s before reconnect …")
        time.sleep(config.getfloat(my_section, 'retry_wait'))
    else:
        # icymonitor was shut down gracefully (due to an icymonitor_stop() call)
        # This might mean MQTT received a config message, so only wait 1s
        logger.info("Icymonitor config changed, waiting " + config.get(my_section, 'config_wait') + "s before reconnect …")
        time.sleep(config.getfloat(my_section, 'config_wait'))
