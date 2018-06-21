#!/usr/bin/env python2
# -*- coding: utf-8 -*-

"""
signalpi.py (Python 2)

Control the SignalPi, a Raspberry Pi with Pimoroni’s blinkt! module.

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


import time
import os
import sys
import atexit
import threading

# get Pimoroni’s blinkt module
try:
    import blinkt
except ImportError:
    exit("SignalPi requires a Raspberry Pi with Pimoroni's 'blinkt' installed.\nInstall with: curl https://get.pimoroni.com/blinkt | bash")


# prepare locks for thread-safe signalling
io_lock = threading.Lock()
sig_lock = threading.Lock()


# cleanup blinkt! board (all lamps off) upon crash/exit/keyboard interrupt
def cleanup():
    io_write(0x00)


# handle a token in the form "yellow", "blink"
# these come directly from the MQTT bus
# For safety reasons, we don’t allow the 230V outputs to be flashed/blinked:
#   For "switch" we ignore the command,
#   for "door", we set it to "on" if flashing or blinking.
def handle_token(signal, value):
    global sig_state, sig_flash, sig_blink
    with sig_lock:
        if signal in signals:
            if value == 'off':
                sig_state = sig_state & ~signals[signal]
                sig_flash = sig_flash & ~signals[signal]
                sig_blink = sig_blink & ~signals[signal]
            elif value == 'on':
                sig_state = sig_state | signals[signal]
                sig_flash = sig_flash & ~signals[signal]
                sig_blink = sig_blink & ~signals[signal]
            elif value == 'flash':
                # in case the desired signal contains "switch" or "door":
                # ignore switch (32), set door (31) to "on" instead of "flash"
                switch_mask = signals[signal] & signals['switch']
                door_mask = signals[signal] & signals['door']
                sig_state = sig_state & (~signals[signal] | switch_mask) | door_mask
                sig_flash = sig_flash | (signals[signal] & ~switch_mask) & ~door_mask
                sig_blink = sig_blink & (~signals[signal] | switch_mask)
            elif value == 'blink':
                # in case the desired signal contains "switch" or "door":
                # ignore switch (32), set door (31) to "on" instead of "blink"
                switch_mask = signals[signal] & signals['switch']
                door_mask = signals[signal] & signals['door']
                sig_state = sig_state & (~signals[signal] | switch_mask) | door_mask
                sig_flash = sig_flash & (~signals[signal] | switch_mask)
                sig_blink = sig_blink | (signals[signal] & ~switch_mask) & ~door_mask
            else:
                pass
            # print "{0:10b}".format(sig_state)
            # print "{0:10b}".format(sig_flash)
            # print "{0:10b}".format(sig_blink)


# write to blinkt! module
# "reversed" is True (1) or False (0), so allows for simple calculation
# blinkt! uses brightness 0.0 .. 1.0, we use 0..100% and calculate ourselves.
# This is also much more fine-grained than the built-in brightness function.
def io_write(state):
    with io_lock:
        for i in range (8):
            # count from 0..7 or from 7..0
            led = (7-i)*reversed + i*(not reversed)
            if state & 1 << i:
                if 1 << i & signals['uv']:
                    # UVI LED, set to current UV Index color
                    r, g, b = tuple([round(x * brightness / 100.0) for x in uv_color])
                    blinkt.set_pixel(led, r, g, b, 1.0)
                else:
                    # normal LED, set to predefined color
                    r, g, b = tuple([round(x * brightness / 100.0) for x in colors[i]])
                    blinkt.set_pixel(led, r, g, b, 1.0)
            else:
                # set LED off
                blinkt.set_pixel(led, 0, 0, 0)
        blinkt.show()

# set blinkt! LED brightness from 0 to 100%
def set_brightness(value):
    global brightness
    try:
        value = int(value)
    except ValueError:
        return  # ignore wrong values
    if value < 0:
        value = 0
    elif value > 100:
        value = 100
    brightness = value
    io_write(sig_state)

# set "reversed" option, just ignore illegal values
def set_reversed(value):
    global reversed
    # Possible boolean values in the configuration.
    BOOLEAN_STATES = {'1': True, 'yes': True, 'true': True, 'on': True,
                      '0': False, 'no': False, 'false': False, 'off': False}
    if value.lower() in BOOLEAN_STATES:
        reversed = BOOLEAN_STATES[value.lower()]
        io_write(sig_state)

# set blinkt! UV Index color
def set_uv(value):
    global uv_color
    try:
        v = float(value)
    except ValueError:
        uv_color = uv_colors['none']
        return

    if v >= 11.0:
        uv_color = uv_colors['purple']
    elif v >= 8.0:
        uv_color = uv_colors['red']
    elif v >= 6.0:
        uv_color = uv_colors['orange']
    elif v >= 3.0:
        uv_color = uv_colors['yellow']
    elif v >= 0.0:
        uv_color = uv_colors['green']
    else:
        pass
    io_write(sig_state)

# main loop, handles blinking and flashing the lamps
# updates happen only via (threaded) MQTT messages
def run():
    global sig_state, sig_flash, sig_blink, sig_prev
    while True:
        for n in range(len(sig_flash_slots)):
            with sig_lock:
                # print n
                # print sig_flash_slots[n]
                # print sig_blink_slots[n]

                if sig_flash_slots[n]:
                    sig_state = sig_state | sig_flash
                else:
                    sig_state = sig_state & ~sig_flash

                if sig_blink_slots[n]:
                    sig_state = sig_state | sig_blink
                else:
                    sig_state = sig_state & ~sig_blink

                if sig_state != sig_prev:
                    io_write(sig_state)
                    sig_prev = sig_state

            time.sleep(slot_duration)


# we have 8 outputs (one byte)
sig_state = 0b00000000
sig_prev  = 0b00000000
sig_flash = 0b00000000
sig_blink = 0b00000000

# we must manually flash or blink the outputs,
# so we use six "timeslots" of 333 ms each
# and set a pattern (0=off, 1=on)
slot_duration = 0.333
sig_flash_slots = [1, 0, 1, 0, 0, 0]
sig_blink_slots = [1, 1, 1, 0, 0, 0]

# signals are binaries (2 bytes), the bits correspond to the 10 relais
#   bits 0..4: group 10: 11, 12, 13, 14, 15 (signal tower 1; 5 lamps)
#   bits 5..7: group 20: 21, 22, 23 (signal tower 2; 3 lamps)
#   bits 8..9: group 30: 31 (230V door light),32 (230V mains switch)
# signals can be combined, i.e. red=red lamps on BOTH signal towers
signals = {
    "white":    0b00000000, # ignore
    "blue":     0b00001000, # LED #3
    "green":    0b00000001, # LED #0
    "yellow":   0b00100010, # LED #1 & # #5
    "red":      0b00000100, # LED #2
    "door":     0b00100000, # LED #5
    "switch":   0b01000000, # LED #6
    "uv":       0b10000000, # LED #7
    "all":      0b11111111  # all 8 LEDs
}

# signal colors (RGB values, mapped to pixels 0..7)
# these are the "official" values
# colors = [
#     (  0, 255,   0), # LED 0 = green
#     (255, 255,   0), # LED 1 = yellow (was too greenish)
#     (255,   0,   0), # LED 2 = red
#     (  0,   0, 255), # LED 3 = blue
#     (  0,   0,   0), # LED 4 = (unused)
#     (255,   0,   0), # LED 5 = red (door)
#     (255,   0, 255), # LED 6 = fuchsia (switch)
#     (  0,   0,   0)  # LED 7 = initially off (set by UVI value)
# ]

# needed to manually tune colors becaus yellow was almost
# indistinguishable from green on my blinkt!
colors = [
    (  0, 160,   0), # LED 0 = green
    (160, 112,   0), # LED 1 = yellow (was too greenish)
    (255,   0,   0), # LED 2 = red
    (  0,   0, 255), # LED 3 = blue
    (  0,   0,   0), # LED 4 = (unused)
    (255,   0,   0), # LED 5 = red (door)
    (255,   0, 255), # LED 6 = fuchsia (switch)
    (  0,   0,   0)  # LED 7 = initially off (set by UVI value)
]

# RGB colors for UV Index LED
# original colors
# uv_colors = {
#     "none":     (  0,   0,   0),
#     "green":    (  0, 255,   0),
#     "yellow":   (255, 255,   0),
#     "orange":   (255, 128,   0),
#     "red":      (255,   0,   0),
#     "purple":   (255,   0, 255)
# }

# manually "tuned" colors
uv_colors = {
    "none":     (  0,   0,   0),
    "green":    (  0, 160,   0),
    "yellow":   (160, 112,   0), # was too greenish
    "orange":   (224,  64,   0), # was too greenish
    "red":      (255,   0,   0),
    "purple":   (255,   0, 255)
}


# register exit function
atexit.register(cleanup)

# due to different mounting situations, LEDs might need to be in reverse order
reversed = False

# perform a lamp test upon initial start (all lamps on for 3 seconds)
brightness = 10 # percent

uv_color = uv_colors['green']
handle_token('all', 'on')
io_write(sig_state)
time.sleep(3.0)

uv_color = uv_colors['none']
handle_token('all', 'off')
io_write(sig_state)


if __name__ == "__main__":
    run()
