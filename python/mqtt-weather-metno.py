#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
mqtt-weather-metno.py (Python 3)

Simple MQTT publisher of weather data using the met.no locationforecast/2.0 API.
Publishes the current temperature, relative humidity, precipitation, pressure,
windspeed and winddirection from a given location.

Uses Rory Sullivan’s metno-locationforecast
https://github.com/Rory-Sullivan/metno-locationforecast
which needs to be installed before:
pip3 install metno-locationforecast
pip3 install python-dateutil

Copyright © 2023 Matthias C. Hormann (@Moonbase59, mhormann@gmx.de)
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
import sys
import configparser
import metno_locationforecast as mnl
import datetime as dt
from dateutil import tz
import math

# Component config from configuration file
# SafeConfigParser was deprecated in Python 3.2
if sys.version_info >= (3, 2):
    config = configparser.ConfigParser()
else:
    config = configparser.SafeConfigParser()

# configfiles are named like "../config/hostname.cfg"
configfile = os.path.dirname(os.path.realpath(__file__)) + '/../config/' + socket.gethostname() + '.cfg'
config.read(configfile)
# define config sections to read
my_section = 'weather-metno'
mqtt_section = 'mqtt'

# Log to STDOUT
logger = logging.getLogger(my_section) # name it like my_section
logger.setLevel(logging.INFO)
consoleHandler = logging.StreamHandler()
logger.addHandler(consoleHandler)

logger.info('Read configuration from ' + configfile)

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
            metno_get_weather()
        else:
            logger.info("Ignoring unknown configuration item " + configitem)


def on_publish(mosq, obj, mid):
    # logger.info("Published message with message ID: "+str(mid))
    pass


def degToCompass(num):
    """Convert degrees to compass abbreviations"""
    val=int((num/22.5)+.5)
    arr=["N","NNE","NE","ENE","E","ESE", "SE", "SSE",
         "S","SSW","SW","WSW","W","WNW","NW","NNW"]
    return arr[(val % 16)]

def feelslike_temperature(temp: float, windspeed: float):
    """Calculate feels like temperature (like met.no)
    see: https://hjelp.yr.no/hc/no/articles/360001695513-Effektiv-temperatur-og-f%C3%B8les-som-"""
    # temp in degrees C at a height of 2m above ground
    # windspeed in km/h at a height of 10m above ground
    W = 13.12 + (0.6215 * temp) - (11.37 * math.pow(windspeed, 0.16)) + \
        (0.3965 * temp * math.pow(windspeed, 0.16))
    return round(W, 1)

# make a LongForecast that uses the LONGEST time intervals available
# (Forecast uses the SHORTEST of 1/6/12 hours)
class LongForecast(mnl.Forecast):

    def _parse_json(self) -> None:
        """Retrieve weather data from json data, using LONGEST time intervals.

        Side Effects:
            self.data
        """
        json = self.json

        last_modified = dt.datetime.strptime(json["headers"]["Last-Modified"], mnl.forecast.HTTP_DATETIME_FORMAT)
        expires = dt.datetime.strptime(json["headers"]["Expires"], mnl.forecast.HTTP_DATETIME_FORMAT)

        updated_at = dt.datetime.strptime(
            json["data"]["properties"]["meta"]["updated_at"], mnl.forecast.YR_DATETIME_FORMAT
        )

        units = json["data"]["properties"]["meta"]["units"]

        intervals = []
        for timeseries in json["data"]["properties"]["timeseries"]:
            start_time = dt.datetime.strptime(timeseries["time"], mnl.forecast.YR_DATETIME_FORMAT)

            variables = {}
            for var_name, var_value in timeseries["data"]["instant"]["details"].items():
                variables[var_name] = mnl.data_containers.Variable(var_name, var_value, units[var_name])

            # Take the longest time interval available.
            hours = 0
            if "next_12_hours" in timeseries["data"]:
                hours = 12
            elif "next_6_hours" in timeseries["data"]:
                hours = 6
            elif "next_1_hours" in timeseries["data"]:
                hours = 1

            end_time = start_time + dt.timedelta(hours=hours)

            if hours != 0:
                symbol_code = timeseries["data"][f"next_{hours}_hours"]["summary"]["symbol_code"]

                try:
                    for var_name, var_value in timeseries["data"][f"next_{hours}_hours"][
                        "details"
                    ].items():
                        variables[var_name] = mnl.data_containers.Variable(var_name, var_value, units[var_name])
                except KeyError:
                    pass
            else:
                symbol_code = None

            intervals.append(mnl.data_containers.Interval(start_time, end_time, symbol_code, variables))

        self.data = mnl.data_containers.Data(last_modified, expires, updated_at, units, intervals)


def metno_get_weather():
    if (not config.has_option(my_section, 'user_agent')
        or not config.has_option(my_section, 'city')
        or not config.has_option(my_section, 'latitude')
        or not config.has_option(my_section, 'longitude')
        or not config.has_option(my_section, 'elevation')
        or not config.has_option(my_section, 'timezone')):
            logger.info("Required configuration items not set, skipping the Weather Underground update")
            return

    # create a Place instance
    city = config.get(my_section, 'city')
    latitude = config.getfloat(my_section, 'latitude')
    longitude = config.getfloat(my_section, 'longitude')
    elevation = config.getint(my_section, 'elevation', fallback=0)
    place = mnl.Place(city, latitude, longitude, elevation)
    
    # create a Forecast instance for the place
    user_agent = config.get(my_section, 'user_agent')
    forecast_type = config.get(my_section, 'forecast_type', fallback='complete')
    save_location = config.get(my_section, 'save_location', fallback='./data')
    base_url = config.get(my_section, 'base_url',
        fallback='https://api.met.no/weatherapi/locationforecast/2.0/')
    
    my_forecast = mnl.Forecast(place, user_agent, forecast_type=forecast_type,
        save_location=save_location, base_url=base_url)
    my_forecast_long = LongForecast(place, user_agent, forecast_type=forecast_type,
        save_location=save_location, base_url=base_url)
    
    # update forecast, result str: 'Data-Not-Expired', 'Data-Not-Modified',
    # or 'Data-Modified'
    result = my_forecast.update()
    result = my_forecast_long.update()
    
    from_tz = tz.tzutc()
    to_tz = tz.gettz(config.get(my_section,'timezone'))
    #to_tz = tz.tzlocal()

    now = dt.datetime.utcnow().replace(tzinfo=from_tz).astimezone(to_tz)
    last_modified = my_forecast.data.last_modified.replace(tzinfo=from_tz).astimezone(to_tz)
    updated_at = my_forecast.data.updated_at.replace(tzinfo=from_tz).astimezone(to_tz)
    expires = my_forecast.data.expires.replace(tzinfo=from_tz).astimezone(to_tz)
    
    # convert units into what we expect
    for interval in my_forecast.data.intervals:
        for variable in interval.variables.values():
            # Change wind speed units to kilometers per hour
            if variable.name == "wind_speed":
                variable.convert_to("km/h")


    # print(my_forecast)
    # print(my_forecast.json)
    # print('Now          : %s' % now.strftime("%F %T"))
    # print('Result       : %s' % result)
    # print('Updated at   : %s' % updated_at.strftime('%F %T'))
    # print('Last modified: %s' % last_modified.strftime('%F %T'))
    # print('Expires      : %s' % expires.strftime('%F %T'))
    # print('')


    # prepare values for MQTT
    observation_epoch = str(int(round(last_modified.timestamp())))
    # construct RFC 822 date; use ctime() to get US day/month names; zone as +HHMM
    ctime = updated_at.ctime()
    observation_time_rfc822 = (f'{ctime[0:3]}, {last_modified.day:02d} {ctime[4:7]}'
        + last_modified.strftime(' %Y %H:%M:%S %z'))
    local_tz_long = config.get(my_section,'timezone')

    # first interval (=current)
    current = my_forecast.data.intervals[0]
    # print(current)
    
    today = dt.date.today()
    forecast0 = my_forecast_long.data.intervals_for(today)
    for interval in forecast0:
      print(interval)
      #print(f"{air_temperature_min}–{air_temperature_max} °C")
      #print(f"Niederschlag: {precipitation_amount} mm")
      print(interval.symbol_code)
    print()
    
    # icon
    icon = current.symbol_code # CAN have "_day", "_night", "_polartwilight" appended!
    wi_icon = 'wi-metno-' + icon # build classname
    # weather description = icon text minus appended variant (will be translated)
    weather = icon.split('_', 1)[0]
    
    temperature = current.variables['air_temperature'].value
    uv = round(current.variables['ultraviolet_index_clear_sky'].value)
    humidity = current.variables['relative_humidity'].value
    pressure = current.variables['air_pressure_at_sea_level'].value
    precipitation = current.variables['precipitation_amount'].value
    windspeed = current.variables['wind_speed'].value
    winddirection = str(int(round(current.variables['wind_from_direction'].value)))
    wind_dir = degToCompass(current.variables['wind_from_direction'].value)
    feelslike = feelslike_temperature(temperature, windspeed)
    
#   Building message info as JSON package
    send_msg = {
        'city': city,
        'latitude': latitude,
        'longitude': longitude,
        'elevation': elevation,
        'observation_epoch': observation_epoch,
        'observation_time_rfc822': observation_time_rfc822,
        'local_tz_long': local_tz_long,
        'icon': wi_icon,
        'temperature': temperature,
        'uv': uv,
        'humidity': humidity,
        'pressure': pressure,
        'precipitation': precipitation,
        'windspeed': windspeed,
        'wind_dir': wind_dir,
        'winddirection': winddirection,
        'feelslike': feelslike,
        'weather': weather
    }

#  Publish data json or single
    status_topic = config.get(mqtt_section, 'base_topic') + config.get(my_section, 'client_topic') + 'status/'
    if config.getboolean(my_section, 'json'):
        mqttclient.publish(status_topic + "json", payload=json.dumps(send_msg), qos=2, retain=True)
        logger.info("Published weather json data to " + status_topic)
    else :
        mqttclient.publish(status_topic + "city", city, retain=True)
        mqttclient.publish(status_topic + "latitude", latitude, retain=True)
        mqttclient.publish(status_topic + "longitude", longitude, retain=True)
        mqttclient.publish(status_topic + "elevation", elevation, retain=True)
        mqttclient.publish(status_topic + "observation_epoch", observation_epoch, retain=True)
        mqttclient.publish(status_topic + "observation_time_rfc822", observation_time_rfc822, retain=True)
        mqttclient.publish(status_topic + "local_tz_long", local_tz_long, retain=True)
        mqttclient.publish(status_topic + "icon", wi_icon, retain=True)
        mqttclient.publish(status_topic + "temperature", temperature, retain=True)
        mqttclient.publish(status_topic + "uv", uv, retain=True)
        mqttclient.publish(status_topic + "humidity", humidity, retain=True)
        mqttclient.publish(status_topic + "pressure", pressure, retain=True)
        mqttclient.publish(status_topic + "precipitation", precipitation, retain=True)
        mqttclient.publish(status_topic + "windspeed", windspeed, retain=True)
        mqttclient.publish(status_topic + "wind_dir", wind_dir, retain=True)
        mqttclient.publish(status_topic + "winddirection", winddirection, retain=True)
        mqttclient.publish(status_topic + "feelslike", feelslike, retain=True)
        mqttclient.publish(status_topic + "weather", weather, retain=True)

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
    metno_get_weather()
    time.sleep(config.getfloat(my_section, 'updaterate'))
