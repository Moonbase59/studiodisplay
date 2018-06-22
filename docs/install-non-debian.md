# Install StudioDisplay on non-Debian-based Linuxes (Manjaro, Arch, …)

## Table of Contents

<!-- MDTOC maxdepth:6 firsth1:2 numbering:0 flatten:0 bullets:1 updateOnSave:1 -->

- [Table of Contents](#table-of-contents)   
- [Will it work?](#will-it-work)   
   - [What will _not_ work (except on a Raspberry Pi)](#what-will-_not_-work-except-on-a-raspberry-pi)   
   - [What might need a little extra work](#what-might-need-a-little-extra-work)   
   - [What _will_ work](#what-_will_-work)   
- [Different package managers (i.e., pacman instead of apt)](#different-package-managers-ie-pacman-instead-of-apt)   
- [My system has Python 3.x as default, not Python 2.x](#my-system-has-python-3x-as-default-not-python-2x)   
- [On my testing machine, `startall.sh` doesn’t work correctly](#on-my-testing-machine-startallsh-doesn’t-work-correctly)   
   - [Missing software](#missing-software)   
   - [Different X terminal emulator](#different-x-terminal-emulator)   

<!-- /MDTOC -->

---

## Will it work?

**The good news: It will work. But you’re a little on your own. Read on.**

### What will _not_ work (except on a Raspberry Pi)

* SignalPi (mqtt-signalpi.py) — Requires a Raspberry Pi with Raspbian or Raspbian Lite.
* UnicornLight (mqtt-unicornlight.py) — Requires a Raspberry Pi with Raspbian or Raspbian Lite.

### What might need a little extra work

* SignalBox (mqtt-signalbox.py) — Requires a driver for the SignalBox hardware. This might have to be manually compiled for your system.
* Stream silence detection — Requires [silentJACK](https://github.com/Moonbase59/silentjack), which might have to be manually compiled for your system.

### What _will_ work

Everything else should (almost) work right out-of-the-box. Read on.

---

## Different package managers (i.e., pacman instead of apt)

Quite easy. Take _Manjaro_ or _Arch_ as example: These use _pacman_ instead of _apt_ for package management.

So whenever I talk about something like

```bash
sudo apt-get install python3 python-pip python3-pip
```

you simply substitute something like:

```bash
sudo pacman -S python3 python-pip python3-pip
```

---

## My system has Python 3.x as default, not Python 2.x

Also quite easy. Just remember whenever we talk about `python3`-something, you’ll probably have that under the name `python`-something. And whenever we use `python`-something in the docs, you’ll probably need `python2`-something instead.

Let’s assume you run on _Manjaro 17.1.10_, which uses _pacman_ instead of _apt_ for package management and also has Python3 as default.

For the example

```bash
sudo apt-get install python3 python-pip python3-pip
```

we would now simply use

```bash
sudo pacman -S python2 python2-pip python-pip
```

and thus install Python2 instead of Python3 (which we already have), and install Python’s _pip_ for Python2 under the name `pip2` and for Python3 under the name `pip`. (For systems with Python2 as default, these would be `pip` for Python2 pip and `pip3` for Python3 pip.)

From now on, when the docs say you should use `pip`, use `pip2` instead; for `pip3`, substitute `pip`.

Thus, installing the Python MQTT client software in the docs says:

```bash
sudo pip install paho-mqtt
sudo pip3 install paho-mqtt
```

But we just do it »the other way round«:

```bash
sudo pip2 install paho-mqtt
sudo pip install paho-mqtt
```

Not _so_ hard, ain’t it? :-)

---

## On my testing machine, `startall.sh` doesn’t work correctly

Possible reasons are …

### Missing software

* You might not have _both_ Python2 _and_ Python3 installed. Both are required for full functionality.

* Maybe you haven’t installed `paho-mqtt` system-wide. It _must_ be available to all users and thus be installed as superuser (or with `sudo`).

* Have you installed `paho-mqtt` for _both_ Python2 _and_ Python3? This is neccessary so all modules can function correctly.

### Different X terminal emulator

* Your system might not have the `x-terminal-emulator`. Use `nano` to edit `startall.sh` and simply substitute _your system’s_ X terminal emulator for all occurrences of `x-terminal-emulator`.

  _Hint:_ On Arch-based systems like _Manjaro_, this is typically `xfce4-terminal`.
