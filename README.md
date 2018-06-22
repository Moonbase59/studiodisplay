# StudioDisplay

**A fast, modular MQTT-based signalling & display solution for Web Radio Stations using IDJC.**  
Or just to make your smart home even smarter.

![StudioDisplay](docs/images/studiodisplay.jpg)

## Table of Contents

<!-- MDTOC maxdepth:6 firsth1:2 numbering:0 flatten:0 bullets:1 updateOnSave:1 -->

- [Table of Contents](#table-of-contents)   
- [Main features](#main-features)   
- [Currently available modules](#currently-available-modules)   
- [Getting Started](#getting-started)   
   - [Make a plan (or sketch)](#make-a-plan-or-sketch)   
   - [Prerequisites](#prerequisites)   
   - [Installing](#installing)   
      - [StudioDisplay software](#studiodisplay-software)   
      - [Weather Underground key and weather source](#weather-underground-key-and-weather-source)   
- [Testing StudioDisplay](#testing-studiodisplay)   
   - [Start all modules](#start-all-modules)   
   - [Check for errors](#check-for-errors)   
   - [Check StudioDisplay fullscreen mode](#check-studiodisplay-fullscreen-mode)   
   - [Perform signalling test](#perform-signalling-test)   
   - [Test with IDJC](#test-with-idjc)   
- [Next steps](#next-steps)   
   - [Check out the documentation!](#check-out-the-documentation)   
   - [Install on a Raspberry Pi 3B/3B+](#install-on-a-raspberry-pi-3b3b)   
   - [Install the IDJC monitor (on your broadcasting machine)](#install-the-idjc-monitor-on-your-broadcasting-machine)   
   - [Install the SignalBox](#install-the-signalbox)   
   - [Install extra SignalPis and UnicornLights](#install-extra-signalpis-and-unicornlights)   
   - [Fine-tuning](#fine-tuning)   
      - [Change »Streaming/On Air« to »On Air/Mic live«](#change-»streamingon-air«-to-»on-airmic-live«)   
      - [Switch languages, locales and measurement units](#switch-languages-locales-and-measurement-units)   
      - [Add a simple studio webcam (MJPEG stream)](#add-a-simple-studio-webcam-mjpeg-stream)   
- [Versioning](#versioning)   
- [Translation](#translation)   
- [Author](#author)   
- [License](#license)   
- [Credits](#credits)   

<!-- /MDTOC -->

## Main features

* Runs on Linux (all modules except SignalPi and UnicornLight may even run on Windows).
* Perfect working integration with [IDJC, the Internet DJ Console](http://idjc.sourceforge.net/) (others planned).
* Standard components (MQTT, Python, Javascript, HTML5/CSS3, USB, IOWarrior, 24VDC signal towers, …).
* Studio Wall Clock.
* Weather (incl. 3-day forecast) from Weather Underground (requires free developer key or better).
* Astronomy data (sunrise/sunset, moonrise/-set/phase etc.).
* Beautiful background images and text color change automatically during the day.
* Up to two 24VDC signal towers (max. 5 + 3 lamp units) using separate SignalBox hardware.
* 2 separate 120/230VAC outputs on SignalBox hardware (for »On Air« light outside studio, etc.).
* Live stream metadata.
* Adjustable silence detection (currently uses [silentJACK](https://github.com/Moonbase59/silentjack)).
* 2 talk timers (general plus announcement overtime).
* Mutes studio monitor speakers when microphone(s) open.
* Call monitor for request lines (for [AVM Fritz!Box](https://en.avm.de/products/fritzbox/) routers, others planned).
* KODI support (shows information, pauses/timeshifts playback when on phone or microphone open).
* Less than 10W when running on a Raspberry Pi (plus monitor and signals).
* Fully customizable using configuration files.
* Nearly all parameters can be changed on-the-fly, using simple MQTT messages.
* Fully translatable into any language using Unicode translation files.
* Compatible with the smarthome architecture proposed in [mqtt-smarthome](https://github.com/mqtt-smarthome/mqtt-smarthome).
* Can easily be integrated into existing MQTT-based smarthome solutions, i.e. other brokers, [FHEM](https://fhem.de/), [openHAB](https://www.openhab.org/) or [Home Assistant](https://www.home-assistant.io/).
* You can have as many StudioDisplays, SignalPis, SignalBoxes, and studios as you want, maybe for different studios or just showing different locations & weather data. All can run on one single MQTT broker.
* Most modules can be used separately (i.e., you might need weather data, astronomy data or a call monitor for your smart home, without running a radio station).

## Currently available modules

* **StudioDisplay:** Shows it all on the big screen (Raspberry Pi 3B/3B+ required, [_Blinkt_](https://shop.pimoroni.com/products/blinkt) module recommended).
* **mqtt-weather-wunderground:** Weather data provider, includes 3-day forecast (free Wunderground API key required).
* **mqtt-astronomy:** Sunrise, sunset, moonrise, moonset, moon phase and phases of the day. Can be used to control ambient lighting and anything dependent on the phase of the day.
* **mqtt-callmonitor-fritz:** Call monitor for [AVM Fritz!Box](https://en.avm.de/products/fritzbox/) routers, can also notify/control a [KODI](https://kodi.tv/)/[LibreELEC](https://libreelec.tv/) media player.
* **mqtt-radio:** Live radio stream metadata display.
* **mqtt-idjc:** Monitor for [IDJC (Internet DJ Console)](http://idjc.sourceforge.net/), provides studio signalling.
* **mqtt-signalbox (SignalBox):** Interface to professional signal towers & »On Air« door light (SignalBox or IOWarrior relais card required).
* **mqtt-signalpi (SignalPi):** The »poor man’s signal tower« (typically used on a Raspberry Pi Zero W, [_Blinkt_](https://shop.pimoroni.com/products/blinkt) module required).
* **mqtt-unicornlight (UnicornLight):** Experimental mini »ambient light« (Raspberry Pi Zero W or better and [_Unicorn pHAT_](https://shop.pimoroni.com/products/unicorn-phat) or [_Unicorn HAT_](https://shop.pimoroni.com/products/unicorn-hat) required).


## Getting Started

These instructions will get you a copy of the project up and running on your local IDJC machine for development and testing purposes. See [Next Steps](#next-steps) for notes on how to deploy the project on a live system.

### Make a plan (or sketch)

Making a little plan (or just a sketch) before you start is helpful. It should show …
* which MQTT broker to use (this might be an existing one, like on a Synology NAS, or the StudioDisplay Pi),
* how many devices of each type you want (i.e., more than one display, more than one SignalPi/SignalBox),
* what the machine’s hostnames are (we recommend self-explanatory names with sequential numbering, like »studio1«, »studiodisplay1«, »studiodisplay2« and so forth).

For starters, consult [docs/architecture.md](docs/architecture.md) which has a nice overview.


### Prerequisites

You need:

* A Linux-based system (your IDJC machine is one). We assume here that you use some Debian-derivative (like Debian, Ubuntu, Linux Mint, Raspbian) but it will also work on other Linux distros. You only have to substitute different commands for your package management (like with Arch Linux or Manjaro, for instance).

  For installation hints on **non-Debian-based Linuxes**, see [docs/install-non-debian.md](docs/install-non-debian.md).

* Python 2 and Python 3 with `pip` and `pip3` installed. These might already be installed in your distro. If not, do a
  ```bash
  sudo apt-get update
  sudo apt-get install python3 python-pip python3-pip
  ```

* A working MQTT broker within in your local network. We recommend [Eclipse Mosquitto](https://mosquitto.org/) which is lightweight and easy to install. You can install it on your local machine as follows:
  ```bash
  sudo apt-get install mosquitto mosquitto-clients
  ```
  Then create the simplest possible configuration for it, using `nano` (or another editor):
  ```bash
  sudo nano /etc/mosquitto/conf.d/`hostname`.conf
  ```
  and enter the following into it:
  ```conf
  # default listener
  port 1883

  # websockets listener
  listener 9001
  protocol websockets
  ```
  You can now save the file (`Ctrl+O`) and exit nano (`Ctrl+X`).

  Restart the mosquitto service so that it will work with the new configuration:

  ```bash
  sudo service mosquitto restart
  ```

* Install the Python MQTT client software:
  ```bash
  sudo pip install paho-mqtt
  sudo pip3 install paho-mqtt
  ```


### Installing

#### StudioDisplay software

Copy or `git clone` the software to your home folder on the Pi, into a folder named `studiodisplay`.

Example:
```bash
cd
git clone https://github.com/Moonbase59/studiodisplay.git
cd studiodisplay
```

Make the Python modules in `~/studiodisplay/python` executable:
```bash
cd ~/studiodisplay/python/
chmod +x mqtt-*.py
chmod +x signaltest.py
```

You *must* have a configuration file set up in `~/studiodisplay/config/` that corresponds with your chosen hostname, i.e. `studio1`.

For starters, just copy and edit the example configuration file:
```bash
cd ~/studiodisplay/config/
cp example.cfg `hostname`.cfg
```
You can edit this file with `nano`, a very minimalistic commandline editor:
```bash
nano `hostname`.cfg
```

Read the comments within the file and make any changes as neccessary.

Changes are written with `Ctrl+O` and then pressing `Enter`. Exit nano with `Ctrl+X`.

#### Weather Underground key and weather source

Get your own [Weather Underground API key](https://www.wunderground.com/weather/api?apiref=b27828e10245d1a1). A developer key for up to 500 requests/day and max. 10/minute can be had for free. If you need more frequent updates than once per 15 minutes, or use StudioDisplay commercially, you might investigate into their other options.

Get the Wunderground Station ID of a reliable weather station near you. Check out their [Wundermap](https://www.wunderground.com/wundermap/?apiref=b27828e10245d1a1).

Enter the API key and the weather station ID you found in your StudioDisplay configuration file, within the `[weather-wunderground]` section:

```bash
cd ~/studiodisplay/config/
nano `hostname`.cfg
```
```conf
[weather-wunderground]
…
wu_api_key = 0000000000000000
…
pws = IHAMBURG2112

```

Save and exit as usual with `Ctrl+O`, `Enter`, `Ctrl+X`.


## Testing StudioDisplay

With the example above, you will not yet have a SignalBox connected (for the signal towers and door light), nor will you have the SignalPi and/or UnicornLight modules running (these require a Raspberry Pi). Nevertheless, you’ll have a running StudioDisplay system that you can test locally (IDJC signalling, weather, web server, StudioDisplay web page, etc.).

### Start all modules

For testing, we have included simple shell scripts that start and stop all modules within separate terminals (so you can see the debug messages):

```bash
cd ~/studiodisplay/
./startall.sh
```

This should (depending on your Linux distro, adapt as neccessary) fire up some terminals and start the Python modules, a simple Python webserver (running on port 8082) and Firefox, displaying the StudioDisplay web page.

### Check for errors

Study each terminal’s output closely, just in case some modules are missing or errors occur (you must enable the Fritz!Box callmonitor by dialling __#96\*5\*__ from a local phone first, specify a valid stream address for your radio station in the config file, and so forth).

### Check StudioDisplay fullscreen mode

When all looks good, watch StudioDisplay in fullscreen mode by pressing `F11` in the browser. Remember, it is optimized to run on a 16:9 screen, so you probably won’t see everything otherwise.

### Perform signalling test

You can now open another terminal and execute the signalling test:

```bash
cd ~/studiodisplay/python/
./signaltest.py
```

Your screen should follow the signals displayed.

### Test with IDJC

Open IDJC and test out various functions, like

* start/stop streaming
* open/close microphone(s)
* stream silence
* check what happens when a song/playlist ends
* test that speakers are muted when a mic goes live


## Next steps

### Check out the documentation!

StudioDisplay can do much more than you suspect after the first tests. To exploit its full potential and make it a real-world, robust and reliable solution fitted to _your_ needs, refer to the documentation in the `docs` folder.

* Read about the [architecture](docs/architecture.md).
* Check out the topic structure ([Freeplane document](docs/StudioStatus\ Topic\ Structure.mm)/[PDF](docs/StudioStatus\ Topic\ Structure.pdf)).
* Read about [translations](docs/translation.md) and how you can help.
* Find much more detailed installation and testing instructions in [docs/install-raspberry-pi.md](docs/install-raspberry-pi.md).

### Install on a Raspberry Pi 3B/3B+

We really recommend installing the main parts of the software on a Raspberry Pi 3B or 3B+. It can run the MQTT broker, the web server and most of the other modules (except the IDJC monitor which you’ll use on your IDJC machine).

Comprehensive and detailed instructions are in [docs/install-raspberry-pi.md](docs/install-raspberry-pi.md).

### Install the IDJC monitor (on your broadcasting machine)

Instructions are in [docs/install-idjc.md](docs/install-idjc.md).

### Install the SignalBox

Further instructions are in [docs/install-signalbox.md](docs/install-signalbox.md).

The SignalBox is a USB-connected ready-made box to drive professional 24VDC signal towers, like WERMA, Patlite, Eaton, Allen Bradley, SIEMENS, Rittal, Pfannenberg. It features a 230VAC mains connection, a built-in 24VDC/1.5A power supply, two M12 (A-coded) industry-standard sockets for connection to the signal towers (max. 5/max. 3 lamp units, respectively) and two 230VAC/10A mains outlets (type CEE 7/4 »Schuko«), one for an external »On Air« doorlight and one for free use (switchable via MQTT command). The well-known _IOWarrior24_ chip is used to control the box, so it can easily be interfaced on Linux, MacOS and Windows systems.

These are your options:
* Get a pre-built box (contact me): Ideal for beginners or professional studios. No building, just buy, connect signal tower and forget. Please specify needed cable length(s) from SignalBox to the signal tower(s).
* Use existing compatible relais boards and build your own signal tower interface: Intermediate, some assembly required, but no hassle with software or drivers.
* Study and modify the code and build your own IOWarrior24-based interface: The hard way, for real enthusiasts. You should know what you do and not be afraid of bits and bytes and driver stuff.

### Install extra SignalPis and UnicornLights

These are usually run on Raspberry Pi Zero W’s and require a _Blinkt_, _UnicornHAT_ (8x8 LEDs) or _UnicornpHAT_ (4x8 LEDs) module. The Pi should have a clean Raspbian Lite (Stretch) installed before you start.

Instructions are in [docs/install-signalpi.md](docs/install-signalpi.md) and [docs/install-unicornlight.md](docs/install-unicornlight.md).

### Fine-tuning

#### Change »Streaming/On Air« to »On Air/Mic live«

Some users asked me if they could have »Streaming« (yellow) changed to »On Air« and »On Air« (red) changed to »Mic live«. If you are more more happy with that, it’s very easy to change in the translation files, for example for the »en-US« locale, you would change the file `~/studiodisplay/config/lang-en-US.json` from

```json
"Ready": "Ready",
"Streaming": "Streaming",
"On Air": "On Air",
"Caller": "Caller",

"On Air, pausing": "On Air, pausing",
"Off Air, resuming": "Off Air, resuming",
```
to
```json
"Ready": "Ready",
"Streaming": "On Air",
"On Air": "Mic live",
"Caller": "Caller",

"On Air, pausing": "Mic live, pausing",
"Off Air, resuming": "Mics closed, resuming",
```

Then reload your StudioDisplay and/or connected browsers and you’re set!

#### Switch languages, locales and measurement units

StudioDisplay is completely localizable and can even display the correct time and date formats for the selected locale. We currently include `de-DE`, `en-GB` and `en-US`, but **need help for further languages**—see [Translation](docs/translation.md).

Let’s assume we have installed StudioDisplay in German (m, °C, hPa, km/h) and now wish to switch to American English (ft, °F, mbar, mph).

Log in to your StudioDisplay system (`studiodisplay1` in our example):

```bash
ssh pi@studiodisplay1
```

Now find the configuration file and switch the locale from `de-DE` to `en-US`:

```bash
nano ~/studiodisplay/config/studiodisplay1.cfg
```

Find the `locale =` entries and change from:

```ini
locale = de-DE
```

to:

```ini
locale = en-US
```

Save and exit.

Now we need to reload the displays. This can easily be accomplished via MQTT:

```bash
mosquitto_pub -h studiodisplay1 -t studiodisplay/all/command/reload -n
```

All connected displays (and browsers) should now reload and display the page in the US-American locale. Watch how the measurement units change from meters, degrees Celsius, hectopascals and kilometers/hour to feet, degrees Fahrenheit, millibars and miles/hour. See the date change from »Dienstag, 29.05.2018« to »Tuesday, 05/29/2018« (and sunrise/sunset times from military to AM/PM time).

**You say you still prefer pressure in inches mercury over the official millibars?** Nothing easier than that:

Open the `en-US` language file and change to your preferred unit and number of decimal places:

```bash
nano ~/studiodisplay/config/lang-en-US.json
```

Find the following:

```json
".pressure": "mbar",
".pressure_text": "mbar",
".pressure_decimals": "0",
```

and change to:

```json
".pressure": "inHg",
".pressure_text": "inHg",
".pressure_decimals": "1",
```

Save and exit as usual.

Again, we need to reload the displays:

```bash
mosquitto_pub -h studiodisplay1 -t studiodisplay/all/command/reload -n
```

(On a normal browser, you can also use `F5` or `Ctrl+F5`.)

Et voilà!


#### Add a simple studio webcam (MJPEG stream)

Using Calin Crisan’s [streamEye](https://github.com/ccrisan/streameye) and a Raspberry Pi camera module, you could even provide a live MJPEG camera stream showing what’s going on in your studio. The Raspberry Pi 3B/3B+ you used for StudioDisplay should be able to handle this extra load.

Copy the file `raspimjpeg.py` from streamEye’s `extras` folder to `/usr/local/bin/`, read the documentation and try everything out. (We recommend [VLC](http://www.videolan.org/vlc/) for watching the stream.)

If you are happy with everything, make the software autostart using

```bash
crontab -e
```
and adding a line like
```conf
@reboot /usr/local/bin/raspimjpeg.py -w 1280 -h 720 -r 25 | /usr/local/bin/streameye -p 8081
```
(Adapt width, height and framerate to your needs.)

StreamEye will then autostart with your Raspberry Pi and provide the webcam stream at  [http://studiodisplay1:8081/](http://studiodisplay1:8081/).

## Versioning

We use [SemVer](http://semver.org/) for versioning. For the versions available, see the [tags on this repository](https://github.com/moonbase59/studiodisplay/tags).

## Translation

Read more in [docs/translation.md](docs/translation.md).

**Help wanted:** We currently have the _en-GB_, _en-US_ and _de-DE_ locales included but are looking for translation into French, Spanish, Dutch, Danish and Russian. Or whatever language _you_ need.

If you think you can help, start with the `~/studiodisplay/config/lang-en-US.json` file, translate and test it in your language and open an issue. It’d be a bonus if you know the correct meteorological terms and the official measurement units for your language and country.

## Author

**Matthias C. Hormann** – [Moonbase59](https://github.com/Moonbase59)

## License

This project is licensed under the GPL-v3 license. See the [COPYING](COPYING) file for details.

## Credits

Too many to mention them all here. Read [CREDITS.md](CREDITS.md).

Thanks to all that make Free and Open Source Software possible!
