# Install the SignalBox

The SignalBox is used to drive up to two real studio signal towers (like WERMA, PATLITE, Eaton, …), plus two separate mains outlets.

It is interfaced and powered by a standard USB 2 connection, using the industry-standard IOWarrior24 chip set. Be sure that your USB 2 (or USB 3) output can handle 500 mA! (The SignalBox will work just fine connected to a Raspberry Pi 3B/3B+ USB port if using the official 2,5A power supply.)

We recommend installing this module on the main Pi, together with all the other software modules. Nevertheless, you can install this module on any other Linux (or even Windows) machine.

If you wish to install this on a Windows machine, please check Code Mercenaries’ [*IO-Warrior SDK Windows*](https://codemercs.com/en/software).

In these installation instructions, we assume that you are on a Linux system, ideally your »main Raspberry Pi« that has the rest of the StudioDisplay software and the MQTT broker installed.

## Requirements

* A SignalBox with attached 24V signal tower(s).

* (Or at least an IOWarrior24 board and the willingness and knowledge to change the code.)

* A kernel that has the IOWarrior kernel modules (all above 2.6 should have these already built-in).

* Code Mercenaries’ `iowkit` library (found in the [*IO-Warrior SDK Linux*](https://www.codemercs.com/en/software))

* StudioDisplay software.


## Copying the software

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

You *must* have a configuration file set up in `~/studiodisplay/config/` that corresponds with your chosen hostname, i.e. `studiodisplay1`.

If you haven’t yet done this step, just copy and edit the example configuration file:
```bash
cd ~/studiodisplay/config/
cp example.cfg studiodisplay1.cfg
```
You can edit this file with `nano`, a very minimalistic commandline editor:
```bash
nano studiodisplay1.cfg
```
Changes are written with `Ctrl+O` and then pressing `Enter`. Exit nano with `Ctrl+X`.


## Update your system’s software

```bash
sudo apt-get update
sudo apt-get upgrade
```

Reboot as neccessary.


## Install Python pip

We might need to install `pip` and `pip3` before we can use it.

```bash
sudo apt-get install python-pip python3-pip
```

## Install the Python MQTT client software

We use Eclipse’s Paho client.

```bash
sudo pip install paho-mqtt
sudo pip3 install paho-mqtt
```

## Configure the MQTT broker to use

Let’s edit the `[mqtt]` section of your config file, `~/studiodisplay/config/studiodisplay1.cfg`, to let the software modules know which broker to talk to. If you followed my instructions on how to install everything on the StudioDisplay Pi, the broker should run on `studiodisplay1`.

```bash
nano ~/studiodisplay/config/studiodisplay1.cfg
```

The `[mqtt]` section should look like this:

```ini
[mqtt]
; ALL modules read from this section to find their broker connection data
; For simplicity and energy-saving, we run the MQTT broker
; on the first StudioDisplay (a Raspberry Pi 3B or 3B+).
host = studiodisplay1
port = 1883
websockets_port = 9001
; Base topic to distinguish different users, etc. Can be left empty.
base_topic =
```

## Configure the SignalBox

While we are still editing the configuration file `~/studiodisplay/config/studiodisplay1.cfg`, let’s set the SignalBox options in the `[signalbox]` section for this system.

```ini
[signalbox]
client_id = signalbox1
; connected, status/, get/, set/, command/ are internally appended to client_topic
; format: device/id/ (id CAN be something else than a number)
client_topic = signalbox/1/
; We subscribe to the studio status topic for displaying its status
subscribe_topic = studio/1/status/
; Initial state of the 230V switch
; For safety reasons, this cannot be blinked or flashed,
; and will not be included in the initial lamp test.
switch = off
```

Now save the file (`Ctrl+O`, `Enter`) and exit the editor (`Ctrl+X`).


## Installation and test

Use `ssh` to connect to your StudioDisplay Pi (or open a terminal if installing on another system):

```bash
ssh pi@studiodisplay1
```

Get and build the *iowkit* library for your system:

```bash
cd ~/Downloads
wget https://www.codemercs.com/downloads/iowarrior/IO-Warrior_SDK_linux.zip
unzip IO-Warrior_SDK_linux.zip
cd Kernel_2.6\ and\ higher/iowkit\ 1.5/library/
tar xzf libiowkit-1.5.0.tar.gz
cd libiowkit-1.5.0/
./configure
make
sudo make install
```

The needed library and header files should now be installed.

Now connect your SignalBox (or compatible IOWarrior device) to the system’s USB. If using a RaspBerry Pi, be sure to use the original Raspberry Pi AC adaptor (2.5A), since we will be powering the SignalBox from the Pi’s USB! Other systems should be able to provide 500 mA to the USB2 port the SignalBox is connected to.

Now test the correct installation:

```bash
cd tests
sudo ./iowkittest
```

It should show you the connected device, its serial number and then give you a nice blinkenlights.

In order to be able to actually use the SignalBox, we will now have to make a so-called "udev rule" that allows us to use the SignalBox without being the superuser (using `sudo` for this would be highly insecure, so we don’t!).

```bash
cd /etc/udev/rules.d/
sudo nano 10-iowarrior.rules
```

Copy and paste the following content into this file:

```
# udev rules for iowarrior device nodes
KERNEL=="iowarrior*", NAME="usb/iowarrior%n", GROUP="users", MODE="0666"
```

Save with `Ctrl+O` and `Enter`, then exit nano using `Ctrl+X`.

To make the changes active, we must restart the udev service:

```bash
sudo service udev restart
```

Then, unplug the SignalBox USB and plug it back in.

Verify that the iowarrior devices are accessible by group "users":

```bash
ls -la /dev/usb/iow*
```

The output should look like this:
```
crw-rw-rw- 1 root users 180, 208 Mai 14 16:11 /dev/usb/iowarrior0
crw-rw-rw- 1 root users 180, 209 Mai 14 16:11 /dev/usb/iowarrior1
```

Note the "rw" rights for "group" and "other", the ownership group "users".

You should now be able to run the above `iowkittest` *without* `sudo`:

```bash
cd ~/Downloads/Kernel_2.6\ and\ higher/iowkit\ 1.5/library/libiowkit-1.5.0/tests/
./iowkittest
```

Now let’s verify that the SignalBox software is running correctly. Assuming you haven’t changed anything in the example configuration, the following should work:

Open two termnals. In terminal 1, start the MQTT SignalBox software:

```bash
cd ~/studiodisplay/python/
./mqtt-signalbox.py
```

It should show that a connection has been establisehd. Also, a short *lamp test* is performed upon startup, i.e., all lamps on both signal towers and the door light should light up, then go off again. (If you have 5 lamps on the first signal tower, the white lamp will come on again.)

Now let’s test some studio tower lights that might happen in real life (i.e., when broadcasting). In terminal 2, try the following:

```bash
mosquitto_pub -h studiodisplay1 -t studio/1/status/green -m on
```

The green *Studio Ready* lamps on both signal towers should light up.

Possible values for the lamp topics (-t) are: `studio/1/status/`, followed by `green`, `yellow`, `red`, `blue` and `switch`, respectively.

Possible values for the message (-m) are: `off`, `on`, `flash` and `blink`. (Not all lamps will work with all messages, for instance, you cannot blink or flash the 230V switch.)

We even included a complete signalling test program:

```bash
cd ~/studiodisplay/python/
./signaltest.py
```

In terminal 1, you should see which signals were received.

Now end the test by pressing `Ctrl+C` in terminal 1 and closing it. Keep terminal 2 open.


### Autostart on a Pi and other headless systems

Of course you want to automatically start this module whenever your system gets booted up.

So lets add an appropriate entry in *crontab* for this:

```bash
crontab -e
```
Now add (or edit) an entry like this:

```crontab
@reboot sleep 5s && /home/pi/studiodisplay/python/mqtt-signalbox.py &
```

Assuming you use *nano* to edit your crontab, now press `Ctrl+O`, `Enter` and `Ctrl+X` to save and exit.

You can verify that everything works correctly by doing a reboot:

```bash
sudo reboot
```

### Autostart on Linux desktop systems

Investigate on the possibilities of your Desktop Environment regarding auto-starting programs and use whatever means are appropriate. The crontab method described above might not work on a desktop machine.

#### Example: Autostart on Linux Mint with the »Cinnamon« desktop

On Linux Mint with the Cinnamon Desktop Environment, simply open the **Menu**, click the **cogwheel button** to open **System Settings**, and select **Preferences → Startup Applications**.

![](images/linux-mint-startup-applications.png)

Then click **Add**, select **Custom command** and fill in the following:

* Name: **SignalBox**
* Command: **/home/matthias/studiodisplay/python/mqtt-signalbox.py &**  
  (Change the user name to _your_ username!)
* Comment: **Start the SignalBox interface**
* Startup delay: You can usually leave this at zero → **0**

Click **Add** again and you will get a nice entry (that can even be switched on and off).

Close the Startup Applications dialog.

Your SignalBox will now be automatically started whenever you logon to your account.

### Lamp test on start

When booting, the lamp test should be performed. SignalBox is now ready to show the signalling going on in your studio.

As per default, it will show the following signals from the other modules (from top to bottom, for easier visualization):

Signal tower(s) (from top to bottom, for easier visualization):

#1 | #2 | Meaning
--- | --- | ---
red | red | On Air (microphone(s) open)
yellow | yellow | Streaming
green | green | Studio ready
blue | — | Optional: Call state (request line)
white | — | Optional: Studio in operation

Mains outlets:

Number | Usage
--- | ---
1 | 230V ON AIR lamp outside the studio, switched with "yellow"
2 | 230V switched outlet, switchable via "switch" (on/off)


#### Configuration file

You can set/modify all relevant options in the `[signalbox]` section of your config file.

As per default, it looks like this:

```ini
[signalbox]
client_id = signalbox1
; connected, status/, get/, set/, command/ are internally appended to client_topic
; format: device/id/ (id CAN be something else than a number)
client_topic = signalbox/1/
; We subscribe to the studio status topic for displaying its status
subscribe_topic = studio/1/status/
; Initial state of the 230V switch
; For safety reasons, this cannot be blinked or flashed,
; and will not be included in the initial lamp test.
switch = off
```

After making changes, you must restart `mqtt-signalbox.py` (or simply reboot your Pi).
