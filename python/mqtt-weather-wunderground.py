#!/usr/bin/env python2
# -*- coding: utf-8 -*-

"""
mqtt-weather-wunderground.py (Python 2)

Simple MQTT publisher of weather data using the WeatherUnderground API.
Publishes the current temperature, relative humidity, precipitation, pressure,
windspeed and winddirection from a given Personal Weather Station

Original idea/script by Simon Vanderveldt:
https://github.com/simonvanderveldt/mqtt-wunderground
Modified to read config from file, export json and follow the mqtt-smarthome architecture.
Modified to allow translations (not used anymore).
Modified to use zmw API URLs, add more data, and provide German phrases.
Modified to use pws and more modern conditions_v11 API.

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
import urllib2
import json
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
my_section = 'weather-wunderground'
mqtt_section = 'mqtt'

# Log to STDOUT
logger = logging.getLogger(my_section) # name it like my_section
logger.setLevel(logging.INFO)
consoleHandler = logging.StreamHandler()
logger.addHandler(consoleHandler)

logger.info('Read configuration from ' + configfile)


# some needed translations
en2de = {
    # in case empty values are returned
    '': '',
    # wind directions (where the wind COMES FROM),
    # as per https://www.wunderground.com/weather/api/d/docs?d=resources/phrase-glossary
    'E': 'O',
    'East': 'O',
    'ENE': 'ONO',
    'ESE': 'OSO',
    'NE': 'NO',
    'NNE': 'NNO',
    'NNW': 'NNW',
    'N': 'N',
    'North': 'N',
    'NW': 'NW',
    'SE': 'SO',
    'S': 'S',
    'South': 'S',
    'SSE': 'SSO',
    'SSW': 'SSW',
    'SW': 'SW',
    'Variable': 'wechselnd',
    'W': 'W',
    'West': 'W',
    'WNW': 'WNW',
    'WSW': 'WSW',
    # weather - current condition phrases,
    # as per https://www.wunderground.com/weather/api/d/docs?d=resources/phrase-glossary
    'Light Drizzle': 'Leichter Nieselregen',
    'Heavy Drizzle': 'Starker Nieselregen',
    'Drizzle': 'Nieselregen',
    'Light Rain': 'Leichter Regen',
    'Heavy Rain': 'Starker Regen',
    'Rain': 'Regen',
    'Light Snow': 'Leichter Schneefall',
    'Heavy Snow': 'Starker Schneefall',
    'Snow': 'Schnee',
    'Light Snow Grains': 'Leichte Schneegriesel',
    'Heavy Snow Grains': 'Starke Schneegriesel',
    'Snow Grains': 'Schneegriesel',
    'Light Ice Crystals': 'Leichte Eiskristallbildung',
    'Heavy Ice Crystals': 'Starke Eiskristallbildung',
    'Ice Crystals': 'Eiskristallbildung',
    'Light Ice Pellets': 'Leichter Eisregen',
    'Heavy Ice Pellets': 'Starker Eisregen',
    'Ice Pellets': 'Eisregen',
    'Light Hail': 'Leichter Hagel',
    'Heavy Hail': 'Starker Hagel',
    'Hail': 'Hagel',
    'Light Mist': 'Leicht neblig',
    'Heavy Mist': 'Stark neblig',
    'Mist': 'Neblig',
    'Light Fog': 'Leichter Nebel',
    'Heavy Fog': 'Starker Nebel',
    'Fog': 'Nebel',
    'Light Fog Patches': 'Stellenweise leichter Nebel',
    'Heavy Fog Patches': 'Stellenweise starker Nebel',
    'Fog Patches': 'Stellenweise Nebel',
    'Light Smoke': 'Leichte Rauchbildung',
    'Heavy Smoke': 'Starke Rauchbildung',
    'Smoke': 'Rauchbildung',
    'Light Volcanic Ash': 'Leichte vulkanische Asche',
    'Heavy Volcanic Ash': 'Starke vulkanische Asche',
    'Volcanic Ash': 'Vulkanische Asche',
    'Light Widespread Dust': 'Leichte Staubschwaden',
    'Heavy Widespread Dust': 'Starke Staubschwaden',
    'Widespread Dust': 'Staubschwaden',
    'Light Sand': 'Leichter Sand',
    'Heavy Sand': 'Starker Sand',
    'Sand': 'Sand',
    'Light Haze': 'Leicht diesig',
    'Heavy Haze': 'Stark diesig',
    'Haze': 'Diesig',
    'Light Spray': 'Leichter Sprühregen',
    'Heavy Spray': 'Starker Sprühregen',
    'Spray': 'Sprühregen',
    'Light Dust Whirls': 'Leichte Staubwirbel',
    'Heavy Dust Whirls': 'Starke Staubwirbel',
    'Dust Whirls': 'Staubwirbel',
    'Light Sandstorm': 'Leichter Sandsturm',
    'Heavy Sandstorm': 'Starker Sandsturm',
    'Sandstorm': 'Sandsturm',
    'Light Low Drifting Snow': 'Leichter niedrig treibender Schnee',
    'Heavy Low Drifting Snow': 'Starker niedrig treibender Schnee',
    'Low Drifting Snow': 'Niedrig treibender Schnee',
    'Light Low Drifting Widespread Dust': 'Leichte niedrig treibende Staubschwaden',
    'Heavy Low Drifting Widespread Dust': 'Starke niedrig treibende Staubschwaden',
    'Low Drifting Widespread Dust': 'Niedrig treibende Staubschwaden',
    'Light Low Drifting Sand': 'Leichter niedrig treibender Sand',
    'Heavy Low Drifting Sand': 'Starker niedrig treibender Sand',
    'Low Drifting Sand': 'Niedrig treibender Sand',
    'Light Blowing Snow': 'Leichtes Schneetreiben',
    'Heavy Blowing Snow': 'Starkes Schneetreiben',
    'Blowing Snow': 'Schneetreiben',
    'Light Blowing Widespread Dust': 'Leichte treibende Staubschwaden',
    'Heavy Blowing Widespread Dust': 'Starke treibende Staubschwaden',
    'Blowing Widespread Dust': 'Treibende Staubschwaden',
    'Light Blowing Sand': 'Leichte Sandverwehungen',
    'Heavy Blowing Sand': 'Starke Sandverwehungen',
    'Blowing Sand': 'Sandverwehungen',
    'Light Rain Mist': 'Leichter Regen und Nebel',
    'Heavy Rain Mist': 'Starker Regen und Nebel',
    'Rain Mist': 'Regen und Nebel',
    'Light Rain Showers': 'Leichte Regenschauer',
    'Heavy Rain Showers': 'Starke Regenschauer',
    'Rain Showers': 'Regenschauer',
    'Light Snow Showers': 'Leichte Schneeschauer',
    'Heavy Snow Showers': 'Starke Schneeschauer',
    'Snow Showers': 'Schneeschauer',
    'Light Snow Blowing Snow Mist': 'Leichtes Schneetreiben und Nebel',
    'Heavy Snow Blowing Snow Mist': 'Starkes Schneetreiben und Nebel',
    'Snow Blowing Snow Mist': 'Schneetreiben und Nebel',
    'Light Ice Pellet Showers': 'Leichte Eisregenschauer',
    'Heavy Ice Pellet Showers': 'Starkes Eisregenschauer',
    'Ice Pellet Showers': 'Eisregenschauer',
    'Light Hail Showers': 'Leichte Hagelschauer',
    'Heavy Hail Showers': 'Starke Hagelschauer',
    'Hail Showers': 'Hagelschauer',
    'Light Small Hail Showers': 'Leichte Graupelschauer',
    'Heavy Small Hail Showers': 'Starke Graupelschauer',
    'Small Hail Showers': 'Graupelschauer',
    'Light Thunderstorm': 'Leichte Gewitter',
    'Heavy Thunderstorm': 'Starke Gewitter',
    'Thunderstorm': 'Gewitter',
    'Light Thunderstorms and Rain': 'Leichte Gewitter und Regen',
    'Heavy Thunderstorms and Rain': 'Starke Gewitter und Regen',
    'Thunderstorms and Rain': 'Gewitter und Regen',
    'Light Thunderstorms and Snow': 'Leichte Gewitter und Schneefall',
    'Heavy Thunderstorms and Snow': 'Starke Gewitter und Schneefall',
    'Thunderstorms and Snow': 'Gewitter und Schneefall',
    'Light Thunderstorms and Ice Pellets': 'Leichte Gewitter und Eisregen',
    'Heavy Thunderstorms and Ice Pellets': 'Starke Gewitter und Eisregen',
    'Thunderstorms and Ice Pellets': 'Gewitter und Eisregen',
    'Light Thunderstorms with Hail': 'Leichte Gewitter mit Hagelschlag',
    'Heavy Thunderstorms with Hail': 'Starke Gewitter mit Hagelschlag',
    'Thunderstorms with Hail': 'Gewitter mit Hagelschlag',
    'Light Thunderstorms with Small Hail': 'Leichte Gewitter mit Graupelschauern',
    'Heavy Thunderstorms with Small Hail': 'Starke Gewitter mit Graupelschauern',
    'Thunderstorms with Small Hail': 'Gewitter mit Graupelschauern',
    'Light Freezing Drizzle': 'Leichter gefrierender Nieselregen',
    'Heavy Freezing Drizzle': 'Starker gefrierender Nieselregen',
    'Freezing Drizzle': 'Gefrierender Nieselregen',
    'Light Freezing Rain': 'Leichter gefrierender Regen',
    'Heavy Freezing Rain': 'Starker gefrierender Regen',
    'Freezing Rain': 'Gefrierender Regen',
    'Light Freezing Fog': 'Leichter überfrierender Nebel',
    'Heavy Freezing Fog': 'Starker überfrierender Nebel',
    'Freezing Fog': 'Überfrierender Nebel',
    'Patches of Fog': 'Stellenweise Nebel',
    'Shallow Fog': 'Flacher Bodennebel',
    'Partial Fog': 'Teilweise Nebel',
    'Overcast': 'Bewölkt',
    'Clear': 'Wolkenlos',
    'Partly Cloudy': 'Stellenweise bewölkt',
    'Mostly Cloudy': 'Überwiegend bewölkt',
    'Scattered Clouds': 'Vereinzelte Wolkenbildung',
    'Small Hail': 'Graupelschauer',
    'Squalls': 'Sturmböen',
    'Funnel Cloud': 'Wolkentrichter',
    'Unknown Precipitation': 'Unbekannter Niederschlag',
    'Unknown': '---',
    # forecast description phrases
    # as per https://www.wunderground.com/weather/api/d/docs?d=resources/phrase-glossary
    'Chance of Flurries': 'Voraussichtlich Schneeböen',
    'Chance of Rain': 'Voraussichtlich Regen',
    'Chance Rain': 'Voraussichtlich Regen',
    'Chance of Freezing Rain': 'Voraussichtlich gefrierender Regen',
    'Chance of Sleet': 'Voraussichtlich Schneeregen',
    'Chance of Snow': 'Voraussichtlich Schneefall',
    'Chance of Thunderstorms': 'Voraussichtlich Gewitter',
    'Chance of a Thunderstorm': 'Voraussichtlich Gewitter',
    'Clear': 'Wolkenlos',
    'Cloudy': 'Bewölkt',
    'Flurries': 'Schneeböen',
    'Fog': 'Nebel',
    'Haze': 'Diesig',
    'Mostly Cloudy': 'Überwiegend bewölkt',
    'Mostly Sunny': 'Überwiegend sonnig',
    'Partly Cloudy': 'Stellenweise bewölkt',
    'Partly Sunny': 'Stellenweise sonnig',
    'Freezing Rain': 'Gefrierender Regen',
    'Rain': 'Regen',
    'Sleet': 'Schneeregen',
    'Snow': 'Schnee',
    'Sunny': 'Sonnig',
    'Thunderstorms': 'Gewitter',
    'Thunderstorm': 'Gewitter',
    'Unknown': '---',
    'Overcast': 'Bewölkt',
    'Scattered Clouds': 'Vereinzelte Wolkenbildung',
    # forecast weekdays
    'Monday': 'Montag',
    'Tuesday': 'Dienstag',
    'Wednesday': 'Mittwoch',
    'Thursday': 'Donnerstag',
    'Friday': 'Freitag',
    'Saturday': 'Samstag',
    'Sunday': 'Sonntag'
}


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
            # update weather directly, don’t wait for next update
            wunderground_get_weather()
            # skip astronomy for now
            # wunderground_get_astronomy()
            wunderground_get_forecast()
        else:
            logger.info("Ignoring unknown configuration item " + configitem)


def on_publish(mosq, obj, mid):
    # logger.info("Published message with message ID: "+str(mid))
    pass


def wunderground_get_weather():
    if not config.has_option(my_section, 'wu_api_key') or not config.has_option(my_section, 'country') or not config.has_option(my_section,'city'):
        logger.info("Required configuration items not set, skipping the Weather Underground update")
        return

    # Parse the WeatherUnderground json response
    # You can specify "Country + City" OR "zmw" OR "pws" (Personal Weather station ID) in the config file.
    # These are used with the following priority (if given):
    #   1. pws, 2. zmw, 3. country + city
    if config.has_option(my_section, 'pws') and config.get(my_section, 'pws'):
        wu_url = "http://api.wunderground.com/api/" + config.get(my_section, 'wu_api_key') + "/conditions_v11/q/pws:" + config.get(my_section, 'pws') + ".json"
    elif config.has_option(my_section, 'zmw') and config.get(my_section, 'zmw'):
        wu_url = "http://api.wunderground.com/api/" + config.get(my_section, 'wu_api_key') + "/conditions_v11/q/zmw:" + config.get(my_section, 'zmw') + ".json"
    elif config.has_option(my_section, 'country') and config.get(my_section, 'country') and config.has_option(my_section, 'city') and config.get(my_section, 'city'):
        wu_url = "http://api.wunderground.com/api/" + config.get(my_section, 'wu_api_key') + "/conditions_v11/q/" + config.get(my_section, 'country') + "/" + config.get(my_section, 'city') + ".json"
    else:
        logger.info("Required configuration items not set: pws, zmw or country+city: Skipping the Weather Underground update")
        return
    logger.info("Getting Weather Underground data from " + wu_url)

    try:
        resonse = urllib2.urlopen(wu_url)
    except urllib2.URLError as e:
        logger.error('URLError: ' + str(wu_url) + ': ' + str(e.reason))
        return None
    except Exception:
        import traceback
        logger.error('Exception: ' + traceback.format_exc())
        return None

    parsed_json = json.load(resonse)
    resonse.close()

    temperature = str(parsed_json['current_observation']['temp_c'])

    # Strip off the last character of the relative humidity because we want an int
    # but we get a % as return from the weatherunderground API
    humidity = str(parsed_json['current_observation']['relative_humidity'][:-1])

    # TODO fix return value for precip from WU API of t/T for trace of rain to 0
    # or sth like 0.1
    try:
        precipitation = str(int(parsed_json['current_observation']['precip_1hr_metric']))
    except ValueError:
        logger.info("Precipitation returned a wrong value '" + str(parsed_json['current_observation']['precip_1hr_metric'][:-1]) +"', replacing with '0'")
        precipitation = str(0)

    pressure = str(parsed_json['current_observation']['pressure_mb'])
    windspeed = str(parsed_json['current_observation']['wind_kph'])
    winddirection = str(parsed_json['current_observation']['wind_degrees']) # where the wind COMES FROM

    # additional info
    # weather = en2de[str(parsed_json['current_observation']['weather'])] # phrase needs translation
    weather = str(parsed_json['current_observation']['weather']) # phrase needs translation
    # wind_dir = en2de[str(parsed_json['current_observation']['wind_dir'])] # needs translation
    wind_dir = str(parsed_json['current_observation']['wind_dir']) # needs translation
    feelslike = str(parsed_json['current_observation']['feelslike_c'])
    icon = str(parsed_json['current_observation']['icon'])
    icon_url = str(parsed_json['current_observation']['icon_url'])
    city = str(parsed_json['current_observation']['display_location']['city'])
    latitude = str(parsed_json['current_observation']['display_location']['latitude'])
    longitude = str(parsed_json['current_observation']['display_location']['longitude'])
    elevation = float(parsed_json['current_observation']['display_location']['elevation'])
    elevation = str(int(round(elevation))) # round to full metres
    observation_epoch = str(parsed_json['current_observation']['observation_epoch'])
    observation_time_rfc822 = str(parsed_json['current_observation']['observation_time_rfc822'])
    local_tz_long = str(parsed_json['current_observation']['local_tz_long'])
    # local_tz_offset = str(parsed_json['current_observation']['local_tz_offset'])
    uv = float(parsed_json['current_observation']['UV'])

#   Building message info as JSON package
    send_msg = {
        'temperature': temperature,
        'humidity': humidity,
        'precipitation': precipitation,
        'pressure': pressure,
        'windspeed': windspeed,
        'winddirection': winddirection,
        'weather': weather,
        'wind_dir': wind_dir,
        'feelslike': feelslike,
        'icon': icon,
        'icon_url': icon_url,
        'city': city,
        'latitude': latitude,
        'longitude': longitude,
        'elevation': elevation,
        'observation_epoch': observation_epoch,
        'observation_time_rfc822': observation_time_rfc822,
        'local_tz_long': local_tz_long,
        # 'local_tz_offset': local_tz_offset,
        'uv': uv
    }

#  Publish data json or single
    status_topic = config.get(mqtt_section, 'base_topic') + config.get(my_section, 'client_topic') + 'status/'
    if config.getboolean(my_section, 'json'):
        mqttclient.publish(status_topic + "json", payload=json.dumps(send_msg), qos=2, retain=True)
        logger.info("Published weather json data to " + status_topic)
    else :
        mqttclient.publish(status_topic + "temperature", temperature, retain=True)
        mqttclient.publish(status_topic + "humidity", humidity, retain=True)
        mqttclient.publish(status_topic + "precipitation", precipitation, retain=True)
        mqttclient.publish(status_topic + "pressure", pressure, retain=True)
        mqttclient.publish(status_topic + "windspeed", windspeed, retain=True)
        mqttclient.publish(status_topic + "winddirection", winddirection, retain=True)
        mqttclient.publish(status_topic + "weather", weather, retain=True)
        mqttclient.publish(status_topic + "wind_dir", wind_dir, retain=True)
        mqttclient.publish(status_topic + "feelslike", feelslike, retain=True)
        mqttclient.publish(status_topic + "icon", icon, retain=True)
        mqttclient.publish(status_topic + "icon_url", icon_url, retain=True)
        mqttclient.publish(status_topic + "city", city, retain=True)
        mqttclient.publish(status_topic + "latitude", latitude, retain=True)
        mqttclient.publish(status_topic + "longitude", longitude, retain=True)
        mqttclient.publish(status_topic + "elevation", elevation, retain=True)
        mqttclient.publish(status_topic + "observation_epoch", observation_epoch, retain=True)
        mqttclient.publish(status_topic + "observation_time_rfc822", observation_time_rfc822, retain=True)
        mqttclient.publish(status_topic + "local_tz_long", local_tz_long, retain=True)
        # mqttclient.publish(status_topic + "local_tz_offset", local_tz_offset, retain=True)
        mqttclient.publish(status_topic + "uv", uv, retain=True)
        logger.info("Published " + my_section + " data to " + status_topic)



def wunderground_get_astronomy():
    if not config.has_option(my_section, 'wu_api_key') or not config.has_option(my_section, 'country') or not config.has_option(my_section,'city'):
        logger.info("Required configuration items not set, skipping the Weather Underground update")
        return

    # Parse the WeatherUnderground json response
    # You can specify "Country + City" OR "zmw" OR "pws" (Personal Weather station ID) in the config file.
    # These are used with the following priority (if given):
    #   1. pws, 2. zmw, 3. country + city
    if config.has_option(my_section, 'pws') and config.get(my_section, 'pws'):
        wu_url = "http://api.wunderground.com/api/" + config.get(my_section, 'wu_api_key') + "/astronomy/q/pws:" + config.get(my_section, 'pws') + ".json"
    elif config.has_option(my_section, 'zmw') and config.get(my_section, 'zmw'):
        wu_url = "http://api.wunderground.com/api/" + config.get(my_section, 'wu_api_key') + "/astronomy/q/zmw:" + config.get(my_section, 'zmw') + ".json"
    elif config.has_option(my_section, 'country') and config.get(my_section, 'country') and config.has_option(my_section, 'city') and config.get(my_section, 'city'):
        wu_url = "http://api.wunderground.com/api/" + config.get(my_section, 'wu_api_key') + "/astronomy/q/" + config.get(my_section, 'country') + "/" + config.get(my_section, 'city') + ".json"
    else:
        logger.info("Required configuration items not set: pws, zmw or country+city: Skipping the Weather Underground update")
        return
    logger.info("Getting Weather Underground data from " + wu_url)

    try:
        response = urllib2.urlopen(wu_url)
    except urllib2.URLError as e:
        logger.error('URLError: ' + str(wu_url) + ': ' + str(e.reason))
        return None
    except Exception:
        import traceback
        logger.error('Exception: ' + traceback.format_exc())
        return None

    parsed_json = json.load(response)
    response.close()

    sunrise = str(parsed_json['moon_phase']['sunrise']['hour'].zfill(2) + ":" + parsed_json['moon_phase']['sunrise']['minute'].zfill(2))
    sunset = str(parsed_json['moon_phase']['sunset']['hour'].zfill(2) + ":" + parsed_json['moon_phase']['sunrise']['minute'].zfill(2))
    moonrise = str(parsed_json['moon_phase']['moonrise']['hour'].zfill(2) + ":" + parsed_json['moon_phase']['moonrise']['minute'].zfill(2))
    moonset = str(parsed_json['moon_phase']['moonset']['hour'].zfill(2) + ":" + parsed_json['moon_phase']['moonrise']['minute'].zfill(2))
    moonpercent = str(parsed_json['moon_phase']['percentIlluminated'])
    moonage = str(parsed_json['moon_phase']['ageOfMoon'])


#   Publish the values we parsed from the feed to the broker

#   Building message info as JSON package
    send_msg = {
        'sunrise': sunrise,
        'sunset': sunset,
        'moonrise': moonrise,
        'moonset': moonset,
        'moonpercent': moonpercent,
        'moonage': moonage
    }

    status_topic = config.get(mqtt_section, 'base_topic') + config.get(my_section, 'client_topic') + 'status/'
    if config.getboolean(my_section, 'json'):
        mqttclient.publish(status_topic + "json", payload=json.dumps(send_msg), qos=2, retain=True)
        logger.info("Published astronomy json data to " + status_topic)
    else :
        mqttclient.publish(status_topic + "sunrise", sunrise, retain=True)
        mqttclient.publish(status_topic + "sunset", sunset, retain=True)
        mqttclient.publish(status_topic + "moonrise", moonrise, retain=True)
        mqttclient.publish(status_topic + "moonset", moonset, retain=True)
        mqttclient.publish(status_topic + "moonpercent", moonpercent, retain=True)
        mqttclient.publish(status_topic + "moonage", moonage, retain=True)
        logger.info("Published astronomy data to " + status_topic)



def wunderground_get_forecast():
    if not config.has_option(my_section, 'wu_api_key') or not config.has_option(my_section, 'country') or not config.has_option(my_section,'city'):
        logger.info("Required configuration items not set, skipping the Weather Underground update")
        return

    # Parse the WeatherUnderground json response
    # You can specify "Country + City" OR "zmw" OR "pws" (Personal Weather station ID) in the config file.
    # These are used with the following priority (if given):
    #   1. pws, 2. zmw, 3. country + city
    if config.has_option(my_section, 'pws') and config.get(my_section, 'pws'):
        wu_url = "http://api.wunderground.com/api/" + config.get(my_section, 'wu_api_key') + "/forecast/q/pws:" + config.get(my_section, 'pws') + ".json"
    elif config.has_option(my_section, 'zmw') and config.get(my_section, 'zmw'):
        wu_url = "http://api.wunderground.com/api/" + config.get(my_section, 'wu_api_key') + "/forecast/q/zmw:" + config.get(my_section, 'zmw') + ".json"
    elif config.has_option(my_section, 'country') and config.get(my_section, 'country') and config.has_option(my_section, 'city') and config.get(my_section, 'city'):
        wu_url = "http://api.wunderground.com/api/" + config.get(my_section, 'wu_api_key') + "/forecast/q/" + config.get(my_section, 'country') + "/" + config.get(my_section, 'city') + ".json"
    else:
        logger.info("Required configuration items not set: pws, zmw or country+city: Skipping the Weather Underground update")
        return
    logger.info("Getting Weather Underground data from " + wu_url)

    # As of June, 2018, Wunderground seem extremely unreliable returning the forecast.
    # Often the value of json['forecast']['txt_forecast']['date'] is an empty string
    # and all values junk, including the simple forecast "epoch" dates
    # which lie back sveral months in the past!
    #
    # Currently, the only way to prevent bad forecasts seems to be checking for
    # an empty date and retry the call – using up calls per minute and day :-(

    # FIXME: This might get us into en endless loop and eat up our allowed hits/day!

    forecast_date = ""

    while not forecast_date:
        try:
            response = urllib2.urlopen(wu_url)
        except urllib2.URLError as e:
            logger.error('URLError: ' + str(wu_url) + ': ' + str(e.reason))
            return None
        except Exception:
            import traceback
            logger.error('Exception: ' + traceback.format_exc())
            return None

        parsed_json = json.load(response)
        response.close()
        forecast_date = str(parsed_json['forecast']['txt_forecast']['date'])
        if not forecast_date:
            logger.info("Got invalid forecast data, retrying in 10s …")
            time.sleep(10)  # TODO: make this configurable

    day = {}
    for d in range (0, 4): # 0-3
        day[d] = {
            'epoch': str(parsed_json['forecast']['simpleforecast']['forecastday'][d]['date']['epoch']),
            'temperature_high': str(parsed_json['forecast']['simpleforecast']['forecastday'][d]['high']['celsius']),
            'temperature_low': str(parsed_json['forecast']['simpleforecast']['forecastday'][d]['low']['celsius']),
            # 'weather': en2de[str(parsed_json['forecast']['simpleforecast']['forecastday'][d]['conditions'])], # needs translation
            'weather': str(parsed_json['forecast']['simpleforecast']['forecastday'][d]['conditions']), # needs translation
            'icon': str(parsed_json['forecast']['simpleforecast']['forecastday'][d]['icon']),
            'icon_url': str(parsed_json['forecast']['simpleforecast']['forecastday'][d]['icon_url']),
            'precipitation': str(parsed_json['forecast']['simpleforecast']['forecastday'][d]['qpf_allday']['mm']),
            'snow': str(parsed_json['forecast']['simpleforecast']['forecastday'][d]['snow_allday']['cm']),
            'windspeed': str(parsed_json['forecast']['simpleforecast']['forecastday'][d]['avewind']['kph']),
            'windspeed_max': str(parsed_json['forecast']['simpleforecast']['forecastday'][d]['maxwind']['kph']),
            'winddirection': str(parsed_json['forecast']['simpleforecast']['forecastday'][d]['avewind']['degrees']),
            # 'wind_dir': en2de[str(parsed_json['forecast']['simpleforecast']['forecastday'][d]['avewind']['dir'])], # needs translation
            'wind_dir': str(parsed_json['forecast']['simpleforecast']['forecastday'][d]['avewind']['dir']), # needs translation
            'humidity': str(parsed_json['forecast']['simpleforecast']['forecastday'][d]['avehumidity']),
            'pop': str(parsed_json['forecast']['simpleforecast']['forecastday'][d]['pop'])
        }

#   Publish the values we parsed from the feed to the broker

#   Building message info as JSON package
#    send_msg = {
#        'sunrise': sunrise,
#        'sunset': sunset
#    }

    status_topic = config.get(mqtt_section, 'base_topic') + config.get(my_section, 'client_topic') + 'status/'
    if config.getboolean(my_section, 'json'):
        mqttclient.publish(status_topic + "json", payload=json.dumps(send_msg), qos=2, retain=True)
        logger.info("Published forecast json data to " + status_topic)
    else :
        for d in day:
            for i in day[d]:
                mqttclient.publish(status_topic + "forecast/" + str(d) + "/" + str(i), day[d][i], retain=True)
            logger.info("Published forecast data for day " + str(d) + " to " + status_topic)



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
    wunderground_get_weather()
    # skip astronomy, it’s unreliable
    # we now do it in mqtt-astronomy, or using SunCalc in index.html
    # wunderground_get_astronomy()
    wunderground_get_forecast()
    time.sleep(config.getfloat(my_section, 'updaterate'))
