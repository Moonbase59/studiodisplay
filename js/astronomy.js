// minifyOnSave, minifierOptions: "charset = utf-8"

/*
astronomy.js

The main JavaScript routines for the astronomy web page.
Requires new browser (tested with Firefox & Chromium 2018-04).

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
*/


var mySection = 'webclient';
var mqttSection = 'mqtt';
config = new ConfigIniParser(); // might use ConfigIniParser("\r\n") for Windows

// create the global vars, will be filled from config
var mqtt;
var reconnectTimeout;
var reconnect;
var host;
var port;
var clientId;
var astronomyTopic;
var commandTopic;
var latitude;
var longitude;
// var locale = 'de-DE'; // target locale for date and number conversions
var locale = Intl.DateTimeFormat().resolvedOptions().locale;
var timezoneLong = Intl.DateTimeFormat().resolvedOptions().timeZone;
var i18n;

// convert a date into HH:mm representation
function date2HHmm(date) {
  var dateoptions = {
    hour: "2-digit", // numeric/2-digit
    minute: "2-digit", // numeric/2-digit
    timeZone: timezoneLong
  };
  return date.toLocaleString(locale, dateoptions);
}

// convert a "HH:mm" string to a date (these come from wunderground)
function HHmm2date(text) {
  var pieces = text.split(":");
  if (pieces.length === 2) {
    hour = parseInt(pieces[0], 10);
    minute = parseInt(pieces[1], 10);
    second = 0;
    // wunderground returns local times, so no need for Date.UTC()
    date = new Date(null, null, null, hour, minute, second);
    return date;
  } else {
    // error
    return null;
  }
}

// convert a "HH:mm" string to a localized version
function HHmm2HHmm(text) {
  var date = HHmm2date(text);
  if (date) {
    return date2HHmm(date);
  } else {
    return '';
  }
}

// return true if number is valid
function numberCheck(value) {
  return !isNaN(value);
}

function myRound(number, precision) {
  var factor = Math.pow(10, precision);
  return Math.round(number * factor) / factor;
}

// helper function to set arbitrary elements on the page
function setElement(element, content, def='') {
  var el = document.getElementById(element);
  if (el) {
    if (content) {
      el.innerHTML = content;
    } else {
      el.innerHTML = def;
    }
  }
}

// shorten a destinationName by cutting off the beginning
// i.e., the weatherTopic path
function shorten(destinationName, beginning=astronomyTopic) {
  return destinationName.replace(beginning, '');
}

// shorten a destinationName by returning only the last part
function shortest(destinationName) {
  return destinationName.split('/').pop();
}

// shorten a destinationName by returning only the last part but one
function parentSubTopic(destinationName) {
  return destinationName.split('/').splice(-2,1).pop();
}

// make RGB from r,g,b payloadString
function makeRGB(msg, opacity=1.0) {
  var result = '';
  var r = msg.split(',').map(item=>item.trim());
  if (r.length == 3) {
    result = 'rgba(' + r[0] + ',' + r[1] + ',' + r[2] + ',' + opacity + ')';
  }
  // console.log(result);
  return result;
}

function onConnect() {
  console.log("Connected to broker " + host + ":" + port);
  console.log("Subscribing to astronomy status at " + astronomyTopic + "#");
  mqtt.subscribe(astronomyTopic + '#');
  // also subscribe to our own command topic
  console.log("Subscribing to device command at " + commandTopic + "#");
  mqtt.subscribe(commandTopic + '#');
}

function onFailure(message) {
  console.log("Connection to " + host + ":" + port + " failed");
  setTimeout(MQTTconnect, reconnectTimeout);
}

function onMessageArrived(msg) {
  out_msg = msg.destinationName + ': ' + msg.payloadString;
  console.log(out_msg);

  // IDs within the DOM correspond to the MQTT destinationName,
  // minus the weatherTopic path defined above (makes them shorter in the HTML)
  var shortName = shorten(msg.destinationName);
  // shortestName is only the rightmost part of a destinationName,
  // we use this if many entries must be handled the same way, like
  // "icon" in "icon", "forecast/0/icon", "forecast/1/icon" and so on.
  var shortestName = shortest(msg.destinationName);

  // special case command channel
  if (msg.destinationName.startsWith(commandTopic)) {
    shortName = shorten(msg.destinationName, commandTopic);
    if (['reload'].includes(shortName)) {
      // We only know one command: brute-force reload.
      // We always reload from the webserver, ignoring the browser cache.
      // This can be used to remotely reload the displays when configuration has changed.
      console.log("RELOADING ...");
      window.location.reload(true); // doesn’t work in Chromium
    } else {
      console.log("Ignoring unknown command " + shortName);
    }
    return;
  }

  // page colors and background from "current"
  if (parentSubTopic(msg.destinationName) == 'current') {
    switch(shortestName){
      case 'background_color':
        document.documentElement.style.backgroundColor = makeRGB(msg.payloadString);
        break;
      case 'text_color':
        document.documentElement.style.color = makeRGB(msg.payloadString, 0.75);
        break;
      case 'shortname':
        document.documentElement.style.backgroundImage = "url('images/" + msg.payloadString + ".jpg')";
        break;
    }
  }

  // dayphase  colors
  if (['background_color', 'text_color', 'shortname'].includes(shortestName)) {
    var p = parentSubTopic(msg.destinationName);
    var elements = document.getElementsByClassName(p);
    var el = document.getElementById(shortName);
    // console.log(elements);
    for (i=0; i < elements.length; i++) {
      switch(shortestName) {
        case 'background_color':
          elements[i].style.backgroundColor = makeRGB(msg.payloadString);
          if (el) {
            el.style.backgroundColor = makeRGB(msg.payloadString);
          }
          break;
        case 'text_color':
          elements[i].style.color = makeRGB(msg.payloadString, 0.75);
          if (el) {
            el.style.color = makeRGB(msg.payloadString, 0.75);
          }
          break;
        case 'shortname':
          elements[i].style.backgroundImage = "url('images/" + msg.payloadString + ".jpg')";
          break;
      }
    }
    return;
  }

  // lamp  colors
  if (['lamp_color'].includes(shortestName)) {
    var el = document.getElementById(shortName);
    if (el) {
      el.style.backgroundColor = makeRGB(msg.payloadString);
      el.style.color = makeRGB('0,0,0', 0.75);
    }
    return;
  }

  // timezone
  if (['timezone'].includes(shortestName)) {
    timezoneLong = msg.payloadString;
  }

  // Update other elements on page identified by id == shortName
  var el = document.getElementById(shortName);
  if (el) {

    // set content
    el.innerHTML = msg.payloadString;

    // translateable day phase
    if (['fullname'].includes(shortestName)) {
      el.innerHTML = i18n.__(msg.payloadString);
    }

    // unix dates will be shown as local time
    if (['epoch', 'ts', 'timestamp'].includes(shortestName)) {
      // dates may be empty (we don’t always have all times)
      if (msg.payloadString) {
        var date = new Date(Number(msg.payloadString) * 1000); // JS works with milliseconds
        var dateoptions = {
          // weekday: "short", // narrow/short/long
          // year: "numeric", // numeric/2-digit
          // month: "2-digit", // numeric/2-digit/narrow/short/long
          // day: "2-digit", // numeric/2-digit
          hour: "2-digit", // numeric/2-digit
          minute: "2-digit", // numeric/2-digit
          // timeZoneName: "short", // short/long
          timeZone: timezoneLong
        };
        el.innerHTML = date.toLocaleString(locale, dateoptions);
      } else {
        el.innerHTML = '';
      }
    }

    // for moon phase, set appropriate moon day (0..27) icon class
    if (['age'].includes(shortestName)) {
      el.innerHTML = '';
      el.className = 'wi wi-moon-' + msg.payloadString;
    }

    // moon illumination
    if (['percent'].includes(shortestName)) {
      el.innerHTML = Number(myRound(msg.payloadString, 0)).toLocaleString(locale);
    }

    if (['always_down'].includes(shortestName)) {
      setElement("moon/set/epoch", i18n.__('always'));
      setElement("moon/rise/epoch", "—");
    }

    if (['always_up'].includes(shortestName)) {
      setElement("moon/set/epoch", "—");
      setElement("moon/rise/epoch", i18n.__('always'));
    }

  }
}

function onConnectionLost(response) {
    console.log("Lost connection to " + response.uri + " (" + response.errorCode.toString() + ")");
    if (response.reconnect) {
      console.log("Automatic reconnect is active.");
    } else {
      console.log("No automatic reconnect will be attempted.");
    }
}

function MQTTconnect() {
  console.log("Connecting to " + host + ":" + port);
  mqtt = new Paho.MQTT.Client(host, port, clientId); // client id generated by Paho
  var options = {
    timeout: 3,
    reconnect: reconnect,
    onSuccess: onConnect,
    onFailure: onFailure
  };
  mqtt.onConnectionLost = onConnectionLost;
  mqtt.onMessageArrived = onMessageArrived;
  mqtt.connect(options);
}

// This will read the .cfg file and then call the "init" function
if (location.hostname) {
  // called from a web server
  var configfile = 'config/' + location.hostname + '.cfg';
} else {
  // called from the filesystem
  // Firefox 59: Works; Chromium 65: Doesn’t work
  var configfile = 'config/unknown_host.cfg';
}
console.log('Read configuration from ' + configfile);
// Need to ignore browser cache, or at least force it to reload.
// Otherwise, Chrome/Chromium will read from cache on reload command!
fetch(configfile, { cache: "reload", mode: "no-cors" })
  .then(response => response.text())
  .then(text => init1(text));

// Init stage 1 -- get configuration
function init1(text) {
  console.log("Init stage 1: Configuration");
  config.parse(text);

  // Set the globals from configuration
  reconnectTimeout = config.getNumber(mySection, 'reconnect_timeout');
  reconnect = config.getBoolean(mySection, 'reconnect');
  host = config.get(mqttSection, 'host');
  port = config.getNumber(mqttSection, 'websockets_port');
  clientId = config.get(mySection, 'client_id');
  astronomyTopic = config.get(mqttSection, 'base_topic') + config.get(mySection, 'astronomy_topic');
  commandTopic = config.get(mqttSection, 'base_topic') + config.get(mySection, 'client_topic') + 'command/';
  latitude = config.getNumber(mySection, 'latitude');
  longitude = config.getNumber(mySection, 'longitude');
  timezoneLong = config.get(mySection, 'timezone');
  locale = config.get(mySection, 'locale'); // target locale for date and number conversions

  document.title = config.get(mySection, 'title');

  // setElement("title", config.get(mySection, "title"));

  // Prepare next step: Read translation file
  var languagefile = 'config/lang-' + locale + '.json';
  // Need to ignore browser cache, or at least force it to reload.
  // Otherwise, Chrome/Chromium will read from cache on reload command!
  fetch(languagefile, { cache: "reload", mode: "no-cors" })
    .then(response => response.json())
    .then(json => init2(json));
}

// Init stage 2 -- get translations and start processes
function init2(json) {
  console.log("Init stage 2: Localization");
  // console.log(json);
  i18n = window.i18n();
  i18n.loadJSON(json, 'messages');
  i18n.setLocale(locale);

  // update all elements on page that need translation

  // These are denoted by class "i18n" and their inner HTML will be translated.
  var elements = document.getElementsByClassName("i18n");
  // console.log(elements);
  for (i=0; i < elements.length; i++) {
    elements[i].innerHTML = i18n.__(elements[i].innerHTML);
  }

  // connect to MQTT broker and get subscriptions going
  MQTTconnect();
}
