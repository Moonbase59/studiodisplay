#!/usr/bin/env python2
# -*- coding: utf-8 -*-

"""
mqtt-idjc.py (Python 2)

Simple MQTT publisher of IDJC data using idjcmonitor.py (installed by IDJC).
Publishes status info to the indicator lights,
i.e. the StudioDisplay software or a signal tower (or both).

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
import sys
import subprocess
import json
import re
import threading
import time
import logging
import socket
import signal # for silence detection
import os
import ConfigParser # Py2: ConfigParser; Py3: configparser

try:
    from idjcmonitor import IDJCMonitor
except ImportError:
    exit("""
Error: Can’t import 'idjcmonitor'.
This usually means you’re running this on a machine with no IDJC installed.
Check: Are you on the machine running IDJC?
       Have you installed IDJC first (it installs 'idjcmonitor')?
""")

try:
    import gobject
except ImportError:
    exit("""
Error: Can’t import 'gobject'.
This usually means that the GTK+ toolkit 'python-gobject' isn’t installed.
Try: sudo apt-get install python-gobject
""")

try:
    import paho.mqtt.client as paho
except ImportError:
    exit("""
Error: Can’t import 'paho.mqtt.client'.
This usually means you haven’t yet installed the MQTT client.
Try: sudo apt-get install python-pip
     sudo pip install paho-mqtt
""")

# Component config from configuration file
config = ConfigParser.SafeConfigParser()
# configfiles are named like "../config/hostname.cfg"
configfile = os.path.dirname(os.path.realpath(__file__)) + '/../config/' + socket.gethostname() + '.cfg'
config.read(configfile)
# define config sections to read
my_section = 'idjc'
mqtt_section = 'mqtt'

# globals for current state
current = {}
current['streams'] = []
current['streamstate'] = {}
current['streams_up'] = 0
current['silence'] = False
current['channels'] = []
current['channelstate'] = {}
current['announcement'] = False
# are the monitor speakers currently muted?
monitor_muted = False
# any KODI instances currently paused?
kodi_paused = False
# process id of the silence detector process group
silentjack_pid = None
# timer thread for overtime
overtime_timer = None

# Log to STDOUT
logger = logging.getLogger(my_section)
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
            if configitem == 'channels':
                show_channelstate()
            elif configitem == 'streams':
                show_streamstate()
        else:
            logger.info("Ignoring unknown configuration item " + configitem)

def on_publish(mosq, obj, mid):
    # logger.info("Published message with message ID: "+str(mid))
    pass


# IDJC stuff

def launch_handler(_, profile, pid):
    status_topic = config.get(mqtt_section, 'base_topic') + config.get(my_section, 'client_topic') + 'status/'
    mqttclient.publish(status_topic + "green", 'on', retain=True)
    if config.has_option(my_section, 'idjc_launch_command'):
        command = config.get(my_section, 'idjc_launch_command')
        if command:
            logger.info("Executing external command: " + command)
            p = subprocess.Popen([command], shell=True, stdout=subprocess.PIPE)
    if config.has_option(my_section, 'silence_detection') and config.getboolean(my_section, 'silence_detection') == True:
        t = threading.Thread(target=run_silentjack)
        t.daemon = True
        t.start()
    # print "Hello to IDJC '%s' with process ID %d." % (profile, pid)
    logger.info("Studio ready with profile " + profile)

def quit_handler(_, profile, pid):
    status_topic = config.get(mqtt_section, 'base_topic') + config.get(my_section, 'client_topic') + 'status/'
    mqttclient.publish(status_topic + "green", 'off', retain=True)
    if config.has_option(my_section, 'idjc_quit_command'):
        command = config.get(my_section, 'idjc_quit_command')
        if command:
            logger.info("Executing external command: " + command)
            p = subprocess.Popen([command], shell=True, stdout=subprocess.PIPE)
    if config.has_option(my_section, 'silence_detection') and config.getboolean(my_section, 'silence_detection') == True:
        # try to kill all in the silence detector’s process group
        logger.info("Stopping silence detection")
        os.killpg(os.getpgid(silentjack_pid), signal.SIGTERM)
    # print "Goodbye to IDJC '%s' with process ID %d." % (profile, pid)
    logger.info("Studio off")

def voip_mode_changed_handler(_, mode):
    """ Handler for the 'voip-mode-changed' signal """
    # mode: 0 = off, 1 = green phone (caller on air), 2 = red phone (talking to caller off air)
    # The BLUE indicator is usually set by an (external) call monitor as follows:
    #   lamp FLASH - incoming call (ringing)
    #   lamp BLINK - call connected
    #   lamp OFF - call disconnected
    # We provide some extra feedback:
    #   mode 1: lamp ON, caller is on air (green phone in IDJC)
    #   mode 2: lamp BLINK, talking to caller locally (red phone in IDJC)
    logger.info("voip mode changed : mode = %d" % mode)
    status_topic = config.get(mqtt_section, 'base_topic') + config.get(my_section, 'client_topic') + 'status/'
    if mode == 0:
        mqttclient.publish(status_topic + "blue", 'off', retain=True)
    elif mode == 1:
        mqttclient.publish(status_topic + "blue", 'on', retain=True)
    elif mode == 2:
        mqttclient.publish(status_topic + "blue", 'blink', retain=True)
    else:
        pass

def streamstate_handler(_, which, state, where):
    global current
    # IDJC internally counts streams from 0, but we want 1..n (like IDJC GUI)
    which += 1
    logger.info("Stream %d is %s on connection %s." % (
                                    which, ("down", "up")[state], where))
    with lock: # tread-safe
        current['streamstate'][which] = state
    show_streamstate(which)

def recordstate_changed_handler(_, numeric_id, recording, where):
    """ Handler for the 'recordstate-changed' signal """
    message = "record state changed : id = %d, recording = %d, where = %s"
    logger.info(message % (numeric_id, recording, where))

def channelstate_changed_handler(_, which, state):
    """ Handler for the 'channelstate-changed' signal """
    global current
    # IDJC internally counts streams from 0, but we want 1..n (like IDJC GUI)
    which += 1
    logger.info("Channel %d is %s." % (which, ("closed", "open")[state]))
    with lock: # thread-safe
        current['channelstate'][which] = state
    show_channelstate(which)

def metadata_handler(_, artist, title, album, songname, music_filename):
    # print "Metadata is: artist: %s, title: %s, album: %s, filename: %s" % (
    #                                 artist, title, album, music_filename)
    logger.info("Playing: " + artist + " - " + title)

def frozen_handler(_, profile, pid, frozen):
    logger.info("IDJC '%s' with process ID %d is %s" % (
                    profile, pid, ("no longer frozen", "frozen")[frozen]))
    indicator = ("on", "flash")[frozen]
    status_topic = config.get(mqtt_section, 'base_topic') + config.get(my_section, 'client_topic') + 'status/'
    mqttclient.publish(status_topic + "green", indicator, retain=True)

def effect_started_handler(_, title, pathname, player):
    # print "Effect player %d is playing %s" % (player, title)
    pass

def effect_stopped_handler(_, player):
    # print "Effect player %d has stopped" % player
    pass

def tracks_finishing_handler(_):
    """ Handler for the 'tracks-finishing' signal """
    # print "tracks finishing"
    # This is a little special: EOM (End-of-medium) is signalled 9 seconds
    # before the end of a song IF a) a player stop, b) an announcement,
    # or c) the end of the playlist follows.
    # We want a signal that (hopefully) "un-signals" itself after 8.0 seconds,
    # (4x the duration of the "flash") so we have enough time to unset it
    # BEFORE (maybe) it is set again by an auto-opening microphone.
    # (We wouldn’t want to switch red off AFTER someone else has set it on!)
    # And it must be non-blocking since we run in a threaded envireonment.
    def end_signal():
        # we can’t simply switch red off (there might be something open)
        # but instead show IDJC’s current channel state again
        show_channelstate()

    status_topic = config.get(mqtt_section, 'base_topic') + config.get(my_section, 'client_topic') + 'status/'
    mqttclient.publish(status_topic + "red", 'flash', retain=True)
    timer = threading.Timer(8.0, end_signal)
    timer.start()

def player_started_handler(_, player):
    # print "Player %s has started" % player
    pass

def player_stopped_handler(_, player):
    # print "Player %s has started" % player
    pass

def announcement_handler(_, player, state, message):
    global current
    # Ignore announcements from interlude player.
    if player in ("left", "right"):
        if state == "active":
            logger.info("New announcement on player %s: %s" % (player, message))
            current['announcement'] = True
        if state == "overtime":
            logger.info("DJ announcement time expired on player %s." % player)
            status_topic = config.get(mqtt_section, 'base_topic') + config.get(my_section, 'client_topic') + 'status/'
            mqttclient.publish(status_topic + "red", 'blink', retain=True)
        if state == "inactive":
            logger.info("Announcement closed on player %s." % player)
            current['announcement'] = False
            # TODO: we MIGHT have to reset RED (not sure, testing required)
            #show_channelstate()

# IDJC auxiliary functions

# show current streamstate to MQTT; "which" starts from 1
def show_streamstate(which=None):
    global current
    # config item can have comma, blank, semicolon, dash or colon as separator
    # create a (numeric) array from config['streams']
    with lock: # thread-safe
        current['streams'] = [int(num) for num in filter(None, re.split("[, ;\-:]", config.get(my_section, 'streams')))]

    if which == None or which in current['streams']:
        # if ALL selected streams are streaming: lamp ON
        # if AT LEAST ONE of selected streams is streaming: lamp BLINKS
        # if NONE of the selected streams are streaming: lamp OFF
        status_topic = config.get(mqtt_section, 'base_topic') + config.get(my_section, 'client_topic') + 'status/'
        all_streams = len(current['streams'])
        streams_up = 0
        streams_list = []
        for k in current['streams']:
            try:
                if current['streamstate'][k]:
                    streams_up += 1
                    streams_list.append(str(k))
            except KeyError:
                pass
        if streams_up == 0:
            mqttclient.publish(status_topic + "yellow", 'off', retain=True)
            mqttclient.publish(status_topic + "streams", '', retain=True)
        elif streams_up < all_streams:
            mqttclient.publish(status_topic + "yellow", 'blink', retain=True)
            mqttclient.publish(status_topic + "streams", ' - '.join(streams_list), retain=True)
        else:
            mqttclient.publish(status_topic + "yellow", 'on', retain=True)
            mqttclient.publish(status_topic + "streams", ' - '.join(streams_list), retain=True)

        current['streams_up'] = streams_up
        logger.info("Stream state is now: " + json.dumps(current['streamstate']))

# show current channel state to MQTT; "which" starts from 1
def show_channelstate(which=None):
    global current, monitor_muted, kodi_paused, overtime_timer

    # this gets fired after the defined default max. talking time
    def signal_overtime():
        global overtime_timer
        logger.info("Overtime: DJ talking longer than %d seconds!" % config.getint(my_section, 'overtime'))
        mqttclient.publish(status_topic + "red", 'blink', retain=True)
        overtime_timer = None

    # config item can have comma, blank, semicolon, dash or colon as separator
    # create a (numeric) array from config['streams']
    with lock: # thread-safe
        current['channels'] = [int(num) for num in filter(None, re.split("[, ;\-:]", config.get(my_section, 'channels')))]

    if which == None or which in current['channels']:
        # if AT LEAST ONE microphone/channel is open: lamp ON
        # if NONE of the selected microphones/channels is open: lamp OFF
        status_topic = config.get(mqtt_section, 'base_topic') + config.get(my_section, 'client_topic') + 'status/'
        all_channels = len(current['channels'])
        channels_up = 0
        channels_list = []
        for k in current['channels']:
            try:
                if current['channelstate'][k]:
                    channels_up += 1
                    channels_list.append(str(k))
            except KeyError:
                pass
        if channels_up > 0:
            # set lamp on
            mqttclient.publish(status_topic + "red", 'on', retain=True)
            mqttclient.publish(status_topic + "channels", ' - '.join(channels_list), retain=True)
            # mute monitor speakers
            if config.has_option(my_section, 'monitor_mute_command'):
                command = config.get(my_section, 'monitor_mute_command')
                if command and not monitor_muted:
                    logger.info("Executing external command: " + command)
                    p = subprocess.Popen([command], shell=True, stdout=subprocess.PIPE)
                    monitor_muted = True
            # show a notice on KODI and pause playback (TV gets timeshifted if so configured)
            if config.getboolean(my_section, 'kodi'):
                command_topic = config.get(my_section, 'kodi_command_topic')
                if command_topic and not kodi_paused:
                    kodi_notice = {
                        "title": _(u"On Air, pausing"),
                        "message": "%s" % ' - '.join(channels_list)
                    }
                    mqttclient.publish(config.get(mqtt_section, 'base_topic') + command_topic + "notify", json.dumps(kodi_notice), retain=True)
                    mqttclient.publish(config.get(mqtt_section, 'base_topic') + command_topic + "playbackstate", 'pause', retain=True)
                    logger.info("KODI notification: " + json.dumps(kodi_notice))
                    logger.info("Pausing KODI …")
                    kodi_paused = True
            # start overtime timeer
            if config.has_option(my_section, 'overtime') \
                and config.getint(my_section, 'overtime') > 0 \
                and not overtime_timer \
                and not current['announcement']:
                overtime_timer = threading.Timer(config.getint(my_section, 'overtime'), signal_overtime)
                overtime_timer.start()
        else:
            # set lamp off
            mqttclient.publish(status_topic + "red", 'off', retain=True)
            mqttclient.publish(status_topic + "channels", '', retain=True)
            # unmute monitor speakers
            if config.has_option(my_section, 'monitor_unmute_command'):
                command = config.get(my_section, 'monitor_unmute_command')
                if command and monitor_muted:
                    logger.info("Executing external command: " + command)
                    p = subprocess.Popen([command], shell=True, stdout=subprocess.PIPE)
                    monitor_muted = False
            # show a notice on KODI and resume playback
            if config.getboolean(my_section, 'kodi'):
                command_topic = config.get(my_section, 'kodi_command_topic')
                if command_topic and kodi_paused:
                    kodi_notice = {
                        "title": _(u"Off Air, resuming"),
                        "message": ""
                    }
                    mqttclient.publish(config.get(mqtt_section, 'base_topic') + command_topic + "notify", json.dumps(kodi_notice), retain=True)
                    mqttclient.publish(config.get(mqtt_section, 'base_topic') + command_topic + "playbackstate", 'resume', retain=True)
                    logger.info("KODI notification: " + json.dumps(kodi_notice))
                    logger.info("Resuming KODI …")
                    kodi_paused = False
            # cancel overtime timer
            if overtime_timer:
                overtime_timer.cancel()
                overtime_timer = None

        logger.info("Channel state is now: " + json.dumps(current['channelstate']))


# emulate Python 3.3+’s shutil.which()
def which(program):
    def is_exe(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file

    return None

# signal handler for silentjack signal (SIGUSR1)
def signal_handler(signum, frame):
    # This is a little special: Silence is signalled after n seconds.
    # We want a signal that "un-signals" itself again after n seconds.
    def end_signal():
        # we can’t simply switch yellow off (there might be something streaming)
        # but instead show IDJC’s current stream state again
        current['silence'] = False
        show_streamstate()

    if current['streams_up'] > 0 and not current['silence']:
        logger.info("SILENCE detected while streaming!")
        status_topic = config.get(mqtt_section, 'base_topic') + config.get(my_section, 'client_topic') + 'status/'
        mqttclient.publish(status_topic + "yellow", 'flash', retain=True)
        current['silence'] = True
        # start timer after which YELLOW will be reset to its original state
        secs = config.getint(my_section, 'silence_detection_seconds')
        timer = threading.Timer(secs, end_signal)
        timer.start()

# start external silentJACK
def run_silentjack():
    global silentjack_pid
    silentjack = which('silentjack')
    if silentjack:
        pid = os.getpid()
        # The following will work with both "old" and "new" versions of silentJACK,
        # see https://github.com/Moonbase59/silentjack/tree/morechannels for my version:
        # Original silentJACK accepts only ONE connection (the last "-c" option),
        # so we try the right channel first, THEN the left channel.
        # Using the original silentJACK, only the left channel will be auto-connected
        # while my version of silentJACK will connect BOTH left and right channels.
        port_r = "idjc_%s:%s" % (config.get(my_section, 'profile'), 'str_out_r')
        port_l = "idjc_%s:%s" % (config.get(my_section, 'profile'), 'str_out_l')
        db = config.getint(my_section, 'silence_detection_db')
        secs = config.getint(my_section, 'silence_detection_seconds')
        command = "%s -c %s -c %s -l %d -p %s -g %s -- kill -SIGUSR1 %d" % (silentjack, port_r, port_l, db, secs, 0, pid)
        logger.info("Starting silence detection: " + command)
        # TODO: Check if we can skip shell and stdout piping, to reduce overhead
        p = subprocess.Popen([command], shell=True, stdout=subprocess.PIPE, preexec_fn=os.setsid)
        silentjack_pid = p.pid
    else:
        logger.info("Silence detector not found: silentjack")

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
#
# while rc == 0:
#     pass

monitor = IDJCMonitor(config.get(my_section, 'profile'))
monitor.connect("launch", launch_handler)
monitor.connect("quit", quit_handler)
monitor.connect("voip-mode-changed", voip_mode_changed_handler)
monitor.connect("streamstate-changed", streamstate_handler)
monitor.connect("recordstate-changed", recordstate_changed_handler)
monitor.connect("channelstate-changed", channelstate_changed_handler)
monitor.connect("metadata-changed", metadata_handler)
monitor.connect("frozen", frozen_handler)
# monitor.connect("effect-started", effect_started_handler)
# monitor.connect("effect-stopped", effect_stopped_handler)
monitor.connect("tracks-finishing", tracks_finishing_handler)
# monitor.connect("player-started", player_started_handler)
# monitor.connect("player-stopped", player_stopped_handler)

# Must try for announcement handler, it might not (yet) be available
# on older IDJC versions
try:
    monitor.connect("announcement", announcement_handler)
except TypeError:
    # monitor.connect() raises TypeError: unknown signal name: announcement
    # if this signal isn’t available
    pass

# signal handler for silence detection
signal.signal(signal.SIGUSR1, signal_handler)

# Initialize threading for MQTT in gobject, otherwise it’ll almost block MQTT!
# NOTE: PyGObject 3.10.0 and 3.10.1 have a bug -- don’t use!
# NOTE: From PyGObject 3.10.2+ on, this requirement has been removed.
gobject.threads_init()

# start the main loop
gobject.MainLoop().run()
