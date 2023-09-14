#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
mqtt-astronomy.py (Python 3)

Simple MQTT publisher of astronomical data at the current location.
This includes sun and moon times as well as phases of the day,
their begin/end times and even suggested RGB values for HTML and real lamps.

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
#import urllib2
import json
import paho.mqtt.client as paho
import time
import logging
import socket
import os
import sys
import configparser as ConfigParser # Py2: ConfigParser; Py3: configparser
import suncalc
import datetime
from email.utils import formatdate # for RFC2822 time strings
import re
import colortemperature as ct

# Component config from configuration file
# SafeConfigParser was deprecated in Python 3.2
if sys.version_info >= (3, 2):
    config = ConfigParser.ConfigParser()
else:
    config = ConfigParser.SafeConfigParser()

# configfiles are named like "../config/hostname.cfg"
configfile = os.path.dirname(os.path.realpath(__file__)) + '/../config/' + socket.gethostname() + '.cfg'
config.read(configfile)
# define config sections to read
my_section = 'astronomy'
mqtt_section = 'mqtt'

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


# Create the callbacks for Mosquitto
def on_connect(self, mosq, obj, rc):
    # show readable connection result (rc)
    logger.info(paho.connack_string(rc))
    if rc == 0:
        # connection successful
        logger.info("Connected to broker " + config.get(mqtt_section, 'host') + ":" + config.get(mqtt_section, 'port') + " as user '" + config.get(mqtt_section, 'username') + "'")

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
            # update directly, don’t wait for next update
            get_astronomy()
        else:
            logger.info("Ignoring unknown configuration item " + configitem)


def on_publish(mosq, obj, mid):
    # logger.info("Published message with message ID: "+str(mid))
    pass


def ts(_date):
    # return a POSIX timestamp (UTC)
    if _date:
        return int(_date.timestamp())
    else:
        return ''

def rfc2822(_date):
    # return a RFC2822 date string
    if _date:
        return formatdate(_date.timestamp(), datetime.tzinfo())
    else:
        return ''

def hhmm(_date):
    # return a zero-padded "HH:mm" string (in local timezone)
    if _date:
        return _date.strftime("%H:%M")
    else:
        return ''

def add_time(_dict, start_topic, _date):
    # add epoch/rfc2822/hhmm times to given topic dict
    _dict[start_topic + 'epoch'] = ts(_date)
    _dict[start_topic + 'rfc2822'] = rfc2822(_date)
    _dict[start_topic + 'hhmm'] = hhmm(_date)

# set Unicorn LED’s color, either °K or R,G,B
def get_RGB_color(value):
    # print(value)
    # color RGB calues may be separated by comma, blank, semicolon, dash, colon in config
    colors = list(filter(None, re.split("[, ;\-:]", value)))
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

    return ','.join([str(r), str(g), str(b)])

def dayphase(_date, times):
    # name in times array, name of dayphase we wish to return
    # returns an array ["phase", "morning/evening"]
    # we have to iterate over the phases of the day because many
    # might not exist (=None), like in polar regions, the sun might not
    # come up or go down for weeks.
    sequence = [
        ['nightEnd',        ['astronomical_twilight', 'morning']],
        ['nauticalDawn',    ['nautical_twilight', 'morning']],
        ['blueHourDawn',    ['blue_hour', 'morning']],
        ['dawn',            ['blue_hour', 'morning']],
        ['blueHourDawnEnd', ['civil_twilight', 'morning']],
        ['sunrise',         ['sunrise_sunset', 'morning']],
        ['sunriseEnd',      ['golden_hour', 'morning']],
        ['goldenHourEnd',   ['daylight', None]],
        ['goldenHour',      ['golden_hour', 'evening']],
        ['sunsetStart',     ['sunrise_sunset', 'evening']],
        ['sunset',          ['civil_twilight', 'evening']],
        ['blueHourDusk',    ['blue_hour', 'evening']],
        ['dusk',            ['blue_hour', 'evening']],
        ['blueHourDuskEnd', ['nautical_twilight', 'evening']],
        ['nauticalDusk',    ['astronomical_twilight', 'evening']],
        ['night',           ['night', None]]
    ]
    # we start in the night and work on
    result = ['night', ['night', None]]
    for p in sequence:
        start = times.get(p[0]) # could be None
        if start:
            if _date >= start:
                result = p
    return result[1]

def get_astronomy():

    now = datetime.datetime.now()
    latitude = config.getfloat(my_section, 'latitude')
    longitude = config.getfloat(my_section, 'longitude')
    timezone = config.get(my_section, 'timezone')

    times = suncalc.getTimes(now, latitude, longitude)
    moonTimes = suncalc.getMoonTimes(now, latitude, longitude)
    moonIllumination = suncalc.getMoonIllumination(now)

    # print(latitude)
    # print(longitude)
    # print(timezone)
    # print(times)
    # print(moonTimes)
    # print(moonIllumination)

    msg = {}

    msg['timestamp'] = ts(now)
    msg['latitude'] = config.getfloat(my_section, 'latitude')
    msg['longitude'] = config.getfloat(my_section, 'longitude')
    msg['country'] = config.get(my_section, 'country')
    msg['city'] = config.get(my_section, 'city')
    msg['timezone'] = config.get(my_section, 'timezone')

    add_time(msg, 'sun/rise/', times.get('sunrise'))
    add_time(msg, 'sun/set/', times.get('sunset'))
    add_time(msg, 'sun/zenith/', times.get('solarNoon'))
    add_time(msg, 'sun/nadir/', times.get('nadir'))

    add_time(msg, 'moon/rise/', moonTimes.get('rise', ''))
    add_time(msg, 'moon/set/', moonTimes.get('set', ''))
    msg['moon/always_up'] = moonTimes.get('alwaysUp', False)
    msg['moon/always_down'] = moonTimes.get('alwaysDown', False)
    msg['moon/percent'] = moonIllumination['fraction'] * 100.0
    msg['moon/age'] = moonIllumination['age']

    add_time(msg, 'times/night/end/', times.get('nightEnd', ''))
    add_time(msg, 'times/night/begin/', times.get('night', ''))
    msg['times/night/shortname'] = 'night'
    msg['times/night/fullname'] = _('Night')
    msg['times/night/background_color'] = '13,18,31' # '13,18,31'
    msg['times/night/text_color'] = '255,255,255'
    msg['times/night/lamp_color'] = get_RGB_color(config.get(my_section, 'night_lamp_color'))

    add_time(msg, 'times/astronomical_twilight/morning/begin/', times.get('nightEnd', ''))
    add_time(msg, 'times/astronomical_twilight/morning/end/', times.get('nauticalDawn', ''))
    add_time(msg, 'times/astronomical_twilight/evening/begin/', times.get('nauticalDusk', ''))
    add_time(msg, 'times/astronomical_twilight/evening/end/', times.get('night', ''))
    msg['times/astronomical_twilight/shortname'] = 'astronomical'
    msg['times/astronomical_twilight/fullname'] = _('Astronomical Twilight')
    msg['times/astronomical_twilight/background_color'] = '16,30,49' # '16,30,49'
    msg['times/astronomical_twilight/text_color'] = '255,255,255'
    msg['times/astronomical_twilight/lamp_color'] = get_RGB_color(config.get(my_section, 'astronomical_twilight_lamp_color'))

    add_time(msg, 'times/nautical_twilight/morning/begin/', times.get('nauticalDawn', ''))
    add_time(msg, 'times/nautical_twilight/morning/end/', times.get('dawn', ''))
    add_time(msg, 'times/nautical_twilight/evening/begin/', times.get('dusk', ''))
    add_time(msg, 'times/nautical_twilight/evening/end/', times.get('nauticalDusk', ''))
    msg['times/nautical_twilight/shortname'] = 'nautical'
    msg['times/nautical_twilight/fullname'] = _('Nautical Twilight')
    msg['times/nautical_twilight/background_color'] = '3,17,76' # '16,57,128'
    msg['times/nautical_twilight/text_color'] = '255,255,255'
    msg['times/nautical_twilight/lamp_color'] = get_RGB_color(config.get(my_section, 'nautical_twilight_lamp_color'))

    add_time(msg, 'times/blue_hour/morning/begin/', times.get('blueHourDawn', ''))
    add_time(msg, 'times/blue_hour/morning/end/', times.get('blueHourDawnEnd', ''))
    add_time(msg, 'times/blue_hour/evening/begin/', times.get('blueHourDusk', ''))
    add_time(msg, 'times/blue_hour/evening/end/', times.get('blueHourDuskEnd', ''))
    msg['times/blue_hour/shortname'] = 'blue'
    msg['times/blue_hour/fullname'] = _('Blue hour')
    msg['times/blue_hour/background_color'] = '16,57,128' # '16,57,128'
    msg['times/blue_hour/text_color'] = '255,255,255'
    msg['times/blue_hour/lamp_color'] = get_RGB_color(config.get(my_section, 'blue_hour_lamp_color'))

    add_time(msg, 'times/civil_twilight/morning/begin/', times.get('dawn', ''))
    add_time(msg, 'times/civil_twilight/morning/end/', times.get('sunrise', ''))
    add_time(msg, 'times/civil_twilight/evening/begin/', times.get('sunset', ''))
    add_time(msg, 'times/civil_twilight/evening/end/', times.get('dusk', ''))
    msg['times/civil_twilight/shortname'] = 'civil'
    msg['times/civil_twilight/fullname'] = _('Civil Twilight')
    msg['times/civil_twilight/background_color'] = '161,158,159'
    msg['times/civil_twilight/text_color'] = '0,0,0'
    msg['times/civil_twilight/lamp_color'] = get_RGB_color(config.get(my_section, 'civil_twilight_lamp_color'))

    add_time(msg, 'times/sunrise_sunset/morning/begin/', times.get('sunrise', ''))
    add_time(msg, 'times/sunrise_sunset/morning/end/', times.get('sunriseEnd', ''))
    add_time(msg, 'times/sunrise_sunset/evening/begin/', times.get('sunsetStart', ''))
    add_time(msg, 'times/sunrise_sunset/evening/end/', times.get('sunset', ''))
    msg['times/sunrise_sunset/shortname'] = 'horizon'
    msg['times/sunrise_sunset/fullname'] = _('Sunrise/Sunset')
    msg['times/sunrise_sunset/background_color'] = '224,87,34' # '145,45,37'
    msg['times/sunrise_sunset/text_color'] = '255,255,255'
    msg['times/sunrise_sunset/lamp_color'] = get_RGB_color(config.get(my_section, 'sunrise_sunset_lamp_color'))

    add_time(msg, 'times/golden_hour/morning/begin/', times.get('sunriseEnd', ''))
    add_time(msg, 'times/golden_hour/morning/end/', times.get('goldenHourEnd', ''))
    add_time(msg, 'times/golden_hour/evening/begin/', times.get('goldenHour', ''))
    add_time(msg, 'times/golden_hour/evening/end/', times.get('sunsetStart', ''))
    msg['times/golden_hour/shortname'] = 'golden'
    msg['times/golden_hour/fullname'] = _('Golden hour')
    msg['times/golden_hour/background_color'] = '246,202,127' #'170,138,98'
    msg['times/golden_hour/text_color'] = '0,0,0'
    msg['times/golden_hour/lamp_color'] = get_RGB_color(config.get(my_section, 'golden_hour_lamp_color'))

    add_time(msg, 'times/daylight/begin/', times.get('goldenHourEnd', ''))
    add_time(msg, 'times/daylight/end/', times.get('goldenHour', ''))
    msg['times/daylight/shortname'] = 'daylight'
    msg['times/daylight/fullname'] = _('Daylight')
    msg['times/daylight/background_color'] = '170,190,215' # '133,168,195'
    msg['times/daylight/text_color'] = '0,0,0'
    msg['times/daylight/lamp_color'] = get_RGB_color(config.get(my_section, 'daylight_lamp_color'))

    # get current
    result = dayphase(now, times)
    if result:
        if result[1]:
            msg['times/current/begin/epoch'] = msg['times/' + result[0] + '/' + result[1] + '/begin/epoch']
            msg['times/current/begin/rfc2822'] = msg['times/' + result[0] + '/' + result[1] + '/begin/rfc2822']
            msg['times/current/begin/hhmm'] = msg['times/' + result[0] + '/' + result[1] + '/begin/hhmm']
            msg['times/current/end/epoch'] = msg['times/' + result[0] + '/' + result[1] + '/end/epoch']
            msg['times/current/end/rfc2822'] = msg['times/' + result[0] + '/' + result[1] + '/end/rfc2822']
            msg['times/current/end/hhmm'] = msg['times/' + result[0] + '/' + result[1] + '/end/hhmm']
        else:
            msg['times/current/begin/epoch'] = msg['times/' + result[0] + '/begin/epoch']
            msg['times/current/begin/rfc2822'] = msg['times/' + result[0] + '/begin/rfc2822']
            msg['times/current/begin/hhmm'] = msg['times/' + result[0] + '/begin/hhmm']
            msg['times/current/end/epoch'] = msg['times/' + result[0] + '/end/epoch']
            msg['times/current/end/rfc2822'] = msg['times/' + result[0] + '/end/rfc2822']
            msg['times/current/end/hhmm'] = msg['times/' + result[0] + '/end/hhmm']

        msg['times/current/shortname'] = msg['times/' + result[0] + '/shortname']
        msg['times/current/fullname'] = msg['times/' + result[0] + '/fullname']
        msg['times/current/background_color'] = msg['times/' + result[0] + '/background_color']
        msg['times/current/text_color'] = msg['times/' + result[0] + '/text_color']
        msg['times/current/lamp_color'] = msg['times/' + result[0] + '/lamp_color']

    # print (msg)

    status_topic = config.get(mqtt_section, 'base_topic') + config.get(my_section, 'client_topic') + 'status/'

    for topic, message in msg.items():
        # print (topic, message)
        mqttclient.publish(status_topic + topic, message, retain=True)
    logger.info("Published astronomy data to " + status_topic)



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
if config.get(mqtt_section, 'username'):
    mqttclient.username_pw_set(config.get(mqtt_section, 'username'), password=config.get(mqtt_section, 'password'))
mqttclient.will_set(connected_topic, 0, qos=2, retain=True)
mqttclient.connect(config.get(mqtt_section, 'host'), config.getint(mqtt_section, 'port'), 60)
mqttclient.publish(connected_topic, 1, qos=1, retain=True)
# Start the Mosquitto loop in a non-blocking way (uses threading)
mqttclient.loop_start()

time.sleep(2)

rc = 0
while rc == 0:
    get_astronomy()
    time.sleep(config.getfloat(my_section, 'updaterate'))
    pass
