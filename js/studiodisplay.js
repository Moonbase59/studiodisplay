// minifyOnSave, minifierOptions: "charset = utf-8"

/*
studiodisplay.js

The main JavaScript routines for the StudioDisplay web page.
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
var username;
var password;
var weatherTopic;
var indicatorTopic;
var radioTopic;
var kodiTopic;
var commandTopic;
var kodiPlaybackState = 0;
var latitude;
var longitude;
// var locale = 'de-DE'; // target locale for date and number conversions
var locale = Intl.DateTimeFormat().resolvedOptions().locale;
var timezoneLong = Intl.DateTimeFormat().resolvedOptions().timeZone;
var i18n;
var updateLighting;

// get phase of day
function dayPhase(date, times) {
  // name in times array, name of dayphase we wish to return
  // returns an array ["phase", "morning/evening"]
  // we have to iterate over the phases of the day because many
  // might not exist (=None), like in polar regions, the sun might not
  // come up or go down for weeks.
  var sequence = [
      ['nightEnd',        'astronomical'],
      ['nauticalDawn',    'nautical'],
      ['blueHourDawn',    'nautical_blue'],
      ['dawn',            'civil_blue'],
      ['blueHourDawnEnd', 'civil'],
      ['sunrise',         'horizon'],
      ['sunriseEnd',      'golden'],
      ['goldenHourEnd',   'daylight'],
      ['goldenHour',      'golden'],
      ['sunsetStart',     'horizon'],
      ['sunset',          'civil'],
      ['blueHourDusk',    'civil_blue'],
      ['dusk',            'nautical_blue'],
      ['blueHourDuskEnd', 'nautical'],
      ['nauticalDusk',    'astronomical'],
      ['night',           'night']
  ];
  // we start in the night and work on
  var result = ['night', 'night'];
  for (var p=0; p < sequence.length; p++) {
    var start = times[sequence[p][0]]; // could be null
    if (start !== null) {
      if (date >= start) {
        result = sequence[p];
      }
    }
  }
  return result[1];
}

// get lighting, based on suncalc
function getLighting(date) {
  var darkText = "rgba(0,0,0,0.75)";
  var brightText = "rgba(255,255,255,0.75)";
  var lighting = {
    // Daylight - Tag -- image has 63.8% brightness → dark text
    'daylight': { fullName: i18n.__("Daylight"), shortName: "daylight", backgroundColor: "#85a8c3", textColor: darkText },
    // Golden Hour - Goldene Stunde -- image has 55.8% brightness → dark text
    'golden': { fullName: i18n.__("Golden hour"), shortName: "golden", backgroundColor: "#aa8a62", textColor: darkText },
    // Sunrise & Sunset - Sonnenauf- und -untergang -- image has 25.8% brightness → bright text
    'horizon': { fullName: i18n.__("Sunrise/Sunset"), shortName: "horizon", backgroundColor: "#912d25", textColor: brightText },
    // Civil Twilight - Bürgerliche Dämmerung -- image has 62.2% brightness → dark text
    'civil': { fullName: i18n.__("Civil Twilight"), shortName: "civil", backgroundColor: "#a19e9f", textColor: darkText },
    // Civil Twilight (Blue Hour) - Bürgerliche Dämmerung (Blaue Stunde) -- image has 58.6% brightness → dark text
    'civil_blue': { fullName: i18n.__("Civil Twilight (Blue hour)"), shortName: "civil_blue", backgroundColor: "#979598", textColor: darkText },
    // Nautical Twilight - Nautische Dämmerung -- image has 21% brightness → bright text
    'nautical': { fullName: i18n.__("Nautical Twilight"), shortName: "nautical", backgroundColor: "#103980", textColor: brightText },
    // Nautical Twilight (Blue Hour)- Nautische Dämmerung (Blaue Stunde) -- image has 21% brightness → bright text
    'nautical_blue': { fullName: i18n.__("Nautical Twilight (Blue hour)"), shortName: "nautical_blue", backgroundColor: "#103980", textColor: brightText },
    // Astronomical Twilight - Astronomische Dämmerung -- image has 11.2% brightness → bright text
    'astronomical': { fullName: i18n.__("Astronomical Twilight"), shortName: "astronomical", backgroundColor: "#101e31", textColor: brightText },
    // Night - Dunkle Nacht -- image has 6.9% brightness → bright text
    'night': { fullName: i18n.__("Night"), shortName: "night", backgroundColor: "#0d121f", textColor: brightText },
    // unknown -- no image, → dark text
    'unknown': { fullName: "", shortName: "unknown", backgroundColor: "#ffffff", textColor: darkText },
  };
  if (date === undefined) {
    var date = new Date();
  }
  var result = 'unknown'; // unknown
  var times = SunCalc.getTimes(date, latitude, longitude);
  // console.log(times);
  // get current
  result = dayPhase(date, times);
  // console.log(result);
  return lighting[result];
}

// convert a date into HH:mm representation
function date2HHmm(date) {
  var dateoptions = {
    hour: "2-digit", // numeric/2-digit
    minute: "2-digit", // numeric/2-digit
    timeZone: timezoneLong
  };
  if (date) {
    return date.toLocaleString(locale, dateoptions);
  } else {
    return '';
  }
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
  // return (value && !Number.isNaN(value)) ? Number(value) : '–';
  // return value && !Number.isNaN(value);
}

// Unit Converter; converts metric data from MQTT to whatever needed
function unitConvert(value, cfrom, cto, decimals=0) {

  function myRound(number, precision) {
    var factor = Math.pow(10, precision);
    return Math.round(number * factor) / factor;
  }

  // lenths (m), conversion to, from anchor
  var lengths = {
    'mm':   { to: function(v) { return v / 1000.0; },          from: function(v) { return v * 1000.0; } },
    'cm':   { to: function(v) { return v / 100.0; },           from: function(v) { return v * 100.0; } },
    'm':    { to: function(v) { return v; },                   from: function(v) { return v; } },
    'in':   { to: function(v) { return v / 39.37007874; },     from: function(v) { return v * 39.37007874; } },
    'ft':   { to: function(v) { return v / 3.280839895; },     from: function(v) { return v * 3.280839895; } }
  };
  // temperatures (K), conversion to, from anchor
  var temperatures = {
    'K':    { to: function(v) { return v; },                   from: function(v) { return v; } },
    'C':    { to: function(v) { return v + 273.15; },          from: function(v) { return v - 273.15; } },
    'F':    { to: function(v) { return (v + 459.67) * 5/9; },  from: function(v) { return v * 9/5 - 459.67 } }
  };
  // speeds (m/s), conversion to, from anchor
  var speeds = {
    'm/s':  { to: function(v) { return v; },                   from: function(v) { return v; } },
    'km/h': { to: function(v) { return v / 3.6; },             from: function(v) { return v * 3.6; } },
    'mph':  { to: function(v) { return v / 2.236936; },        from: function(v) { return v * 2.236936; } }
  };

  // pressures (Pa), conversion to, from anchor
  var pressures = {
    'Pa':   { to: function(v) { return v; },                   from: function(v) { return v; } },
    'bar':  { to: function(v) { return v * 100000.0; },        from: function(v) { return v / 100000.0; } },
    'mbar': { to: function(v) { return v * 100.0; },           from: function(v) { return v / 100.0; } },
    'hPa':  { to: function(v) { return v * 100.0; },           from: function(v) { return v / 100.0; } },
    'mmHg': { to: function(v) { return v * 133.322387415; },   from: function(v) { return v / 133.322387415; } },
    'inHg': { to: function(v) { return v * 3386.39; },         from: function(v) { return v / 3386.39; } }
  };
  var known = Object.assign({}, lengths, temperatures, speeds, pressures);

  if (known.hasOwnProperty(cfrom) && known.hasOwnProperty(cto)) {
    // it’s a known unit
    if (lengths.hasOwnProperty(cfrom) && lengths.hasOwnProperty(cto)) {
      // ok, from and to are both lengths
      // return value converted to anchor and back from anchor
      return myRound(lengths[cto].from(lengths[cfrom].to(value)), decimals);
    } else if (temperatures.hasOwnProperty(cfrom) && temperatures.hasOwnProperty(cto)) {
      // ok, from and to are both temperatures
      return myRound(temperatures[cto].from(temperatures[cfrom].to(value)), decimals);
    } else if (speeds.hasOwnProperty(cfrom) && speeds.hasOwnProperty(cto)) {
      // ok, from and to are both speeds
      return myRound(speeds[cto].from(speeds[cfrom].to(value)), decimals);
    } else if (pressures.hasOwnProperty(cfrom) && pressures.hasOwnProperty(cto)) {
      // ok, from and to are both pressures
      return myRound(pressures[cto].from(pressures[cfrom].to(value)), decimals);
    } else {
      // error
      return value;
    }
  } else {
    // error
    return value;
  }
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

// helper function to set progress indicator on the page
function setProgress(element, content) {
  var el = document.getElementById(element);
  if (el) {
    // console.log(el.parentNode);
    var parentWidth = el.parentNode.clientWidth;
    var parentHeight = el.parentNode.clientHeight;
    // console.log(parentWidth);
    var newWidth = parentWidth / 100 * Number(content);
    if (newWidth > parentWidth) {
      newWidth = parentWidth;
    }
    // console.log(newWidth);
    el.style.width = newWidth.toString() + 'px';
    el.style.height = parentHeight + 'px';
  }
}

// helper function to set a player icon (stop, play, pause)
// requires Fontawesome Font to be installed
function setPlayerIcon(element, content) {
  var el = document.getElementById(element);
  if (el) {
    el.className = 'fa fa-' + content;
  }
}

// update lighting (i.e., look of website)
function setLighting(date) {
  if (!date) {
    var date = new Date();
  }
  var l = getLighting(date);
  // need to get times again, for DOM element updates
  var times = SunCalc.getTimes(date, latitude, longitude);
  // console.log(latitude, longitude, timezoneLong)
  // console.log(times);

  // Wunderground delivers bad moonrise/moonset times, so use our own
  var moontimes = SunCalc.getMoonTimes(date, latitude, longitude);
  // console.log(moontimes);

  // Wunderground delivers shit like moonage:29, so we
  // have to calculate this ourselves!
  var moon = SunCalc.getMoonIllumination(date);
  // console.log(moon);
  // calculate moon day 0..27 from phase percentage
  // var moonage = Math.floor(moon['phase'] * 100.0 / (100.0 / 28));
  var moonage = moon['age'];
  var moonpercent = Math.round(moon['fraction'] * 100.0);
  // console.log(moonage);
  // console.log(moonpercent);

  // for moon phase, set appropriate moon day (0..27) icon class
  var el = document.getElementById("lighting/moonage");
  if (el) {
    el.innerHTML = '';
    el.className = 'wi wi-moon-' + moonage.toString();
  }
  // while we are at it, also set moon illumination from our own calculations
  setElement("lighting/moonpercent", moonpercent, '0');

  console.log("Current lighting condition: " + l.fullName);
  setElement("lighting/fullname", l.fullName);

  // show sunrise/sunset, moonrise/moonset
  setElement("lighting/sunrise", date2HHmm(times.sunrise));
  setElement("lighting/noon", date2HHmm(times.solarNoon));
  setElement("lighting/sunset", date2HHmm(times.sunset));

  if (moontimes.set) {
    setElement("lighting/moonset", date2HHmm(moontimes.set));
  } else {
    setElement("lighting/moonset", "—");
  }
  if (moontimes.rise) {
    setElement("lighting/moonrise", date2HHmm(moontimes.rise));
  } else {
    setElement("lighting/moonrise", "—");
  }
  if (moontimes.alwaysDown) {
    setElement("lighting/moonset", i18n.__('always'));
    setElement("lighting/moonrise", "—");
  }
  if (moontimes.alwaysUp) {
    setElement("lighting/moonset", "—");
    setElement("lighting/moonrise", i18n.__('always'));
  }

  // show blue and golden hours, if so requested
  setElement("lighting/blueHourDawn/begin", date2HHmm(times.blueHourDawn));
  setElement("lighting/blueHourDawn/end", date2HHmm(times.blueHourDawnEnd));
  setElement("lighting/blueHourDusk/begin", date2HHmm(times.blueHourDusk));
  setElement("lighting/blueHourDusk/end", date2HHmm(times.blueHourDuskEnd));
  setElement("lighting/goldenHourDawn/begin", date2HHmm(times.sunriseEnd));
  setElement("lighting/goldenHourDawn/end", date2HHmm(times.goldenHourEnd));
  setElement("lighting/goldenHourDusk/begin", date2HHmm(times.goldenHour));
  setElement("lighting/goldenHourDusk/end", date2HHmm(times.sunsetStart));

  document.documentElement.style.backgroundColor = l.backgroundColor;
  document.documentElement.style.color = l.textColor;
  document.documentElement.style.backgroundImage = "url('images/" + l.shortName + ".jpg')";
}

// shorten a destinationName by cutting off the beginning
// i.e., the weatherTopic path
function shorten(destinationName, beginning=weatherTopic) {
  return destinationName.replace(beginning, '');
}

// shorten a destinationName by returning only the last part
function shortest(destinationName) {
  return destinationName.split('/').pop();
}

function onConnect() {
  console.log("Connected to broker " + host + ":" + port + " as user '" + username + "'");
  console.log("Subscribing to weather status at " + weatherTopic + "#");
  mqtt.subscribe(weatherTopic + '#');
  console.log("Subscribing to radio status at " + radioTopic + "#");
  mqtt.subscribe(radioTopic + '#');
  console.log("Subscribing to studio status at " + indicatorTopic + "#");
  mqtt.subscribe(indicatorTopic + '#');
  console.log("Subscribing to Kodi status at " + kodiTopic + "#");
  mqtt.subscribe(kodiTopic + "#");
  // also subscribe to our own command topic
  console.log("Subscribing to device command at " + commandTopic + "#");
  mqtt.subscribe(commandTopic + '#');
}

function onFailure(message) {
  console.log("Connection to " + host + ":" + port + " as user '" + username + "' failed");
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

  // update latitude, longitude, timezone for suncalc and background
  if (shortName == "latitude") {
    latitude = Number(msg.payloadString);
  }
  if (shortName == "longitude") {
    longitude = Number(msg.payloadString);
  }
  if (shortName == "local_tz_long") {
    timezoneLong = msg.payloadString;
  }

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
  }

  // special case KODI
  if (msg.destinationName.startsWith(kodiTopic)) {
    shortName = shorten(msg.destinationName, kodiTopic);
    if (['title', 'playbackstate', 'progress'].includes(shortName)) {
      var decodedMsg = JSON.parse(msg.payloadString);
      // console.log(decodedMsg);
      // console.log(shortName);
      switch (shortName) {
        case 'title':
          if (kodiPlaybackState > 0) {
            setElement('kodi/title', decodedMsg.val, '\u00A0'); // empty → &nbsp;
            // make 1st letter uppercase
            var type = decodedMsg.kodi_details.type.charAt(0).toUpperCase() + decodedMsg.kodi_details.type.slice(1);
            // translate mediatype, can be one of:
            //   unknown, channel, episode, movie, musicvideo, picture, radio, song, video
            setElement('kodi/title/type', i18n.__(type));
            setElement('kodi/title/label', decodedMsg.kodi_details.label);
          }
          break;
        case 'playbackstate':
          kodiPlaybackState = decodedMsg.val;
          if (kodiPlaybackState <= 0) {
            setPlayerIcon('kodi/state', 'stop'); // stop
            setElement('kodi/title', '');
            setElement('kodi/title/type', '');
            setElement('kodi/title/label', '');
            setProgress('kodi/progress', "0");
          }
          if (kodiPlaybackState == 1) {
            setPlayerIcon('kodi/state', 'play'); // play
          } else if (kodiPlaybackState == 2) {
            setPlayerIcon('kodi/state', 'pause'); // pause
          }
          break;
        case 'progress':
          if (kodiPlaybackState > 0) {
            setProgress('kodi/progress', decodedMsg.val);
          }
          break;
      }
    }
    return;
  }

  // special case radio (need to take care of empty title)
  // topics are like "base_topic/radio/1/status/title"
  // but in the HTML—for simplicity—coded as "radio/status/title"
  // we want to remove the id part ("1/") since we only subscribe to ONE
  if (msg.destinationName.startsWith(radioTopic)) {
    shortName = shorten(msg.destinationName, radioTopic);

    if (['title'].includes(shortName)) {
      setElement('radio/status/' + shortName, msg.payloadString, '\u00A0'); // empty → &nbsp;
    } else {
      setElement('radio/status/' + shortName, msg.payloadString);
    }
    return;
  }

  // special case indicator lamps: modify classes, not content
  // whatever they really do is defined in the CSS :-)
  // topics are like "base_topic/studio/1/status/yellow"
  // but in the HTML—for simplicity—coded as "studio/status/yellow"
  // we want to remove the id part ("1/") since we only subscribe to ONE
  if (msg.destinationName.startsWith(indicatorTopic)) {
    var lamp = shorten(msg.destinationName, indicatorTopic);
    var el = document.getElementById('studio/status/' + lamp);
    if (el) {
      if (['white', 'green', 'yellow', 'red', 'blue', 'switch'].includes(lamp)) {
        // it's a lamp
        switch (msg.payloadString) {
          case 'on':
            console.log(lamp + ": " + msg.payloadString);
            if (el.classList.contains('flash')) { el.classList.remove('flash'); };
            if (el.classList.contains('blink')) { el.classList.remove('blink'); };
            if (!el.classList.contains('on')) { el.classList.add('on'); };
            break;
          case 'off':
            console.log(lamp + ": " + msg.payloadString);
            if (el.classList.contains('flash')) { el.classList.remove('flash'); };
            if (el.classList.contains('blink')) { el.classList.remove('blink'); };
            if (el.classList.contains('on')) { el.classList.remove('on'); };
            break;
          case 'flash':
            console.log(lamp + ": " + msg.payloadString);
            if (el.classList.contains('on')) { el.classList.remove('on'); };
            if (el.classList.contains('blink')) { el.classList.remove('blink'); };
            if (!el.classList.contains('flash')) { el.classList.add('flash'); };
            break;
          case 'blink':
            console.log(lamp + ": " + msg.payloadString);
            if (el.classList.contains('on')) { el.classList.remove('on'); };
            if (el.classList.contains('flash')) { el.classList.remove('flash'); };
            if (!el.classList.contains('blink')) { el.classList.add('blink'); };
            break;
        }
      } else {
        // it's not a lamp but maybe a text for a lamp
        el.innerHTML = msg.payloadString;
      }
      return;
    }
  }

  // Update other elements on page identified by id == shortName
  var el = document.getElementById(shortName);
  if (el) {

    // set content
    el.innerHTML = msg.payloadString;

    // The following require Eric’s wonderful weather icons having been installed.
    // for winddirection, set appropriate icon class to show compass
    if (shortestName == "winddirection") {
      el.innerHTML = '';
      el.className = 'wi wi-wind from-' + msg.payloadString + '-deg';
    }
    // for moon phase, set appropriate day (0..27) icon class
    // Wunderground returns senseless data like "29", so we skip that here
    // an calculate ourselves in setLighting()
    // if (shortName == "moonage") {
    //   el.innerHTML = '';
    //   el.className = 'wi wi-moon-' + msg.payloadString;
    // }

    // show current weather icon, modify class
    if (shortestName == "icon") {
      el.innerHTML = '';
      el.className = 'wi ' + msg.payloadString;
    }

    // Numbers to be converted to localized representation -- shortName
    // temperatures
    if (['temperature', 'feelslike'].includes(shortName)) {
      el.innerHTML = unitConvert(Number(msg.payloadString), 'C', i18n.__('.temperature'), 1).toLocaleString(locale);
    }
    // pressures
    if (['pressure'].includes(shortName)) {
      el.innerHTML = unitConvert(Number(msg.payloadString), 'hPa', i18n.__('.pressure'), Number(i18n.__('.pressure_decimals'))).toLocaleString(locale);
    }
    // elevation
    if (['elevation'].includes(shortName)) {
      el.innerHTML = unitConvert(Number(msg.payloadString), 'm', i18n.__('.elevation')).toLocaleString(locale);
    }

    // Numbers to be converted to localized representation -- shortestName
    // temperatures
    if (['temperature_low', 'temperature_high'].includes(shortestName)) {
      el.innerHTML = unitConvert(Number(msg.payloadString), 'C', i18n.__('.temperature')).toLocaleString(locale);
    }
    // speeds
    if (['windspeed', 'windspeed_max'].includes(shortestName)) {
      el.innerHTML = unitConvert(Number(msg.payloadString), 'km/h', i18n.__('.speed'), Number(i18n.__('.speed_decimals'))).toLocaleString(locale);
    }

    // precipitation (can return 'None')
    if (['precipitation'].includes(shortestName)) {
      if (numberCheck(msg.payloadString)) {
        el.innerHTML = unitConvert(Number(msg.payloadString), 'mm', i18n.__('.precipitation'), Number(i18n.__('.precipitation_decimals'))).toLocaleString(locale);
      } else {
        el.innerHTML = '–'; // &ndash;
      }
    }
    // snowfall (can return 'None')
    if (['snow'].includes(shortestName)) {
      if (numberCheck(msg.payloadString)) {
        el.innerHTML = unitConvert(Number(msg.payloadString), 'cm', i18n.__('.snowfall'), Number(i18n.__('.snowfall_decimals'))).toLocaleString(locale);
      } else {
        el.innerHTML = '–'; // &ndash;
      }
    }
    // the rest
    if (['humidity', 'pop', 'uv'].includes(shortestName)) {
      el.innerHTML = Number(msg.payloadString).toLocaleString(locale);
      // handle UVI colors
      if (shortestName == 'uv') {
        var v = Number(msg.payloadString);
        // console.log(v);
        switch (true) {
          case v >= 11.0:
            el.className = 'uv-color uv-color-purple';
            el.title = i18n.__("Risk: Extreme");
            break;
          case v >= 8.0:
            el.className = 'uv-color uv-color-red';
            el.title = i18n.__("Risk: Very high");
            break;
          case v >= 6.0:
            el.className = 'uv-color uv-color-orange';
            el.title = i18n.__("Risk: High");
            break;
          case v >= 3.0:
            el.className = 'uv-color uv-color-yellow';
            el.title = i18n.__("Risk: Moderate");
            break;
          case v >= 0.0:
            el.className = 'uv-color uv-color-green';
            el.title = i18n.__("Risk: Low");
            break;
          default:
            el.className = 'uv-color uv-color-none';
            el.title = "";
            break;
        }
      }
    }

    // translateable weather
    // wind directions like "ESE", weather condition text
    if (['wind_dir', 'weather'].includes(shortestName)) {
      el.innerHTML = i18n.__(msg.payloadString);
    }

    // observation_epoch will be shown as local time
    if (shortName == "observation_epoch") {
      var date = new Date(Number(msg.payloadString) * 1000); // JS works with milliseconds
      var dateoptions = {
        weekday: "short", // narrow/short/long
        year: "numeric", // numeric/2-digit
        month: "2-digit", // numeric/2-digit/narrow/short/long
        day: "2-digit", // numeric/2-digit
        hour: "2-digit", // numeric/2-digit
        minute: "2-digit", // numeric/2-digit
        timeZoneName: "short", // short/long
        timeZone: timezoneLong
      };
      el.innerHTML = date.toLocaleString(locale, dateoptions);
    }
    // sunrise, sunset, moonrise, moonset are in local "HH:mm" format, convert
    if (['sunrise', 'sunset', 'moonrise', 'moonset'].includes(shortName)) {
      el.innerHTML = HHmm2HHmm(msg.payloadString);
    }
    // forecast epoch will be shown as localized full weekdaay name
    if (shortestName == "epoch") {
      var date = new Date(Number(msg.payloadString) * 1000); // JS works with milliseconds
      var dateoptions = {
        weekday: "long", // narrow/short/long
        timeZone: timezoneLong
      };
      el.innerHTML = date.toLocaleString(locale, dateoptions);
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
    userName: username,
    password: password,
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
  username = config.get(mqttSection, 'username');
  password = config.get(mqttSection, 'password');
  weatherTopic = config.get(mqttSection, 'base_topic') + config.get(mySection, 'weather_topic');
  indicatorTopic = config.get(mqttSection, 'base_topic') + config.get(mySection, 'indicator_topic');
  radioTopic = config.get(mqttSection, 'base_topic') + config.get(mySection, 'radio_topic');
  kodiTopic = config.get(mqttSection, 'base_topic') + config.get(mySection, 'kodi_topic');
  commandTopic = config.get(mqttSection, 'base_topic') + config.get(mySection, 'client_topic') + 'command/';
  latitude = config.getNumber(mySection, 'latitude');
  longitude = config.getNumber(mySection, 'longitude');
  timezoneLong = config.get(mySection, 'timezone');
  locale = config.get(mySection, 'locale'); // target locale for date and number conversions

  document.title = config.get(mySection, 'title');

  setElement("title", config.get(mySection, "title"));

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

  // Fill all elements denoted by classes like ".temperature" with
  // their respective unit text from the language file (".temperature_text")
  var list = ['.temperature', '.speed', '.pressure', '.precipitation', '.snowfall', '.elevation'];
  for (i=0; i < list.length; i++) {
    var elements = document.getElementsByClassName(list[i]);
    for (j=0; j < elements.length; j++) {
      elements[j].innerHTML = i18n.__(list[i] + '_text');
    }
  }

  // These are denoted by class "i18n" and their inner HTML will be translated.
  var elements = document.getElementsByClassName("i18n");
  // console.log(elements);
  for (i=0; i < elements.length; i++) {
    elements[i].innerHTML = i18n.__(elements[i].innerHTML);
  }

  // start updating Lighting Conditions every minute
  updateLighting = setInterval(function() { setLighting() }, 60000);
  // connect to MQTT broker and get subscriptions going
  MQTTconnect();
  // Initially, set current Lighting Conditions once
  //setLighting(new Date(2018,3,4,12,15));
  setLighting();
}
