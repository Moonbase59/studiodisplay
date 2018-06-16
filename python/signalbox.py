#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
signalbox.py (Python 2)

Control the SignalBox using Code Mercenaries’ IOWKit library
(which must be installed before, see documentation).

The SignalBox is a hardware device that controls:
  - a 24 VDC signal tower #1 (max. 5 lamps, i.e. WERMA, Patlite, Eaton, …)
  - a 24 VDC signal tower #2 (max. 3 lamps, i.e. WERMA, Patlite, Eaton, …)
  - a mains outlet (115/230 VAC) #1 for an external door light ("On Air")
  - a mains outlet (115/230 VAC) #2 for an external switchable device

It is connected to the PC/Raspberry Pi via USB 2 (500 mA max.)
and uses the well-known IOWarrior24 for interfacing.

Completely assembled and tested units can be bought from me. The units work
with both 115 and 230 VAC (50/60 Hz) and have a built-in 24 VDC power-supply
for the signal towers. Currently, the two mains outlets are only available as
German "Schuko" sockets ("Schutzkontaktsteckdose", CEE 7/3 socket). These
sockets can be used with CEE 7/4 ("Schuko"), CEE 7/7, CEE 7/16 Alternative II
("Europlug") and CEE 7/17 plugs.

This software *should* work on Windows platforms, but we only tested on Linux.

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


import ctypes
from ctypes import *
import time
import os
import sys
import atexit


# Load libiowkit.so
if sys.platform == 'linux2':
    iowkit = ctypes.CDLL("libiowkit.so")
elif sys.platform == 'win32':
    iowkit = ctypes.WinDLL('iowkit.dll')
else:
    NotImplementedError("Loading the iowkit library not implemented yet")
    exit()


#######################################################################
# iowkit definitions and declarations

# TODO: manually declare all function arguments and return types because
# ctypes does not seem to recognize 64bit pointers on its own
iowkit.IowKitOpenDevice.restype = ctypes.c_voidp
iowkit.IowKitVersion.restype = ctypes.c_char_p
iowkit.IowKitGetProductId.argtypes = [ctypes.c_voidp]
iowkit.IowKitGetProductId.restype = ctypes.c_ulong
iowkit.IowKitRead.argtypes = [ctypes.c_voidp,
                              ctypes.c_ulong, ctypes.c_voidp, ctypes.c_ulong]
iowkit.IowKitCloseDevice.argtypes = [ctypes.c_voidp]
iowkit.IowKitGetDeviceHandle.argtypes = [ctypes.c_ulong]
iowkit.IowKitGetDeviceHandle.restype = ctypes.c_voidp
iowkit.IowKitGetNumDevs.restype = ctypes.c_ulong
iowkit.IowKitSetTimeout.argtypes = [ctypes.c_voidp, ctypes.c_ulong]
iowkit.IowKitReadImmediate.argtypes = [
    ctypes.c_voidp, ctypes.POINTER(ctypes.c_ulong)]
iowkit.IowKitGetSerialNumber.argtypes = [ctypes.c_voidp, ctypes.c_wchar_p]

# TODO: datatypes and definitions
IOW_PIPE_IO_PINS = ctypes.c_ulong(0)
IOW_PIPE_SPECIAL_MODE = ctypes.c_ulong(1)

IOWKIT_PRODUCT_ID_IOW40 = 0x1500
IOWKIT_PRODUCT_ID_IOW24 = 0x1501
IOWKIT_PRODUCT_ID_IOW56 = 0x1503


IOWKIT_MAX_PIPES = ctypes.c_ulong(2)
IOWKIT_MAX_DEVICES = ctypes.c_ulong(16)

IOWKIT24_IO_REPORT = ctypes.c_ubyte * 3
IOWKIT24_SPECIAL_REPORT = ctypes.c_ubyte * 8

IOWKIT40_IO_REPORT = ctypes.c_ubyte * 5
IOWKIT40_SPECIAL_REPORT = ctypes.c_ubyte * 8

IOWKIT56_IO_REPORT = ctypes.c_ubyte * 8
IOWKIT56_SPECIAL_REPORT = ctypes.c_ubyte * 64

IOWKIT_SERIAL = ctypes.c_wchar * 9


# cleanup relais board (all lamps off) upon crash/exit/keyboard interrupt
def cleanup():
    io_write(0x0000)
    # Don't forget to close!
    iowkit.IowKitCloseDevice(ioHandle)


# handle a token in the form "yellow", "blink"
# these come directly from the MQTT bus
# For safety reasons, we don’t allow the 230V outputs to be flashed/blinked:
#   For "switch" we ignore the command,
#   for "door", we set it to "on" if flashing or blinking.
def handle_token(signal, value):
    global sig_state, sig_flash, sig_blink
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


# write to the IOWarrior24 connected via USB,
# i.e. the RK10-USB V1.2 relais board
def io_write(state):
    report = IOWKIT24_IO_REPORT(0x00, ~(state & 0xff), ~(state >> 8 & 0xff))
    iowkit.IowKitWrite(c_ulong(ioHandle), IOW_PIPE_IO_PINS, ctypes.byref(report), sizeof(IOWKIT24_IO_REPORT))


# main loop, handles blinking and flashing the lamps
# updates happen only via (threaded) MQTT messages
def run():
    global sig_state, sig_flash, sig_blink, sig_prev
    while True:
        for n in range(len(sig_flash_slots)):
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

            # print "{0:10b}".format(sig_state)

            time.sleep(0.333)


# Open iowarrior
ioHandle = iowkit.IowKitOpenDevice()


if ioHandle == 0:
    raise IOError("No device detected, ioHandle: " + str(ioHandle))
    exit()
else:
    # Get number of IOWs
    numdevs = iowkit.IowKitGetNumDevs()
    print "Found", numdevs, "devices."
    if numdevs <= 0:
        exit()
    else:
        atexit.register(cleanup)


# Get ProductID
# we only handle our board (uses IOWarrior24)
pid = iowkit.IowKitGetProductId(ioHandle)
if pid == IOWKIT_PRODUCT_ID_IOW40:
    print "Device Type: IO-Warrior40"
if pid == IOWKIT_PRODUCT_ID_IOW24:
    print "Device Type: IO-Warrior24"
if pid == IOWKIT_PRODUCT_ID_IOW56:
    print "Device Type: IO-Warrior56"

if pid != IOWKIT_PRODUCT_ID_IOW24:
    raise IOError("This is not a SignalBox!")

# we have 10 outputs
sig_state = 0b0000000000
sig_prev  = 0b0000000000
sig_flash = 0b0000000000
sig_blink = 0b0000000000

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
    "white":    0b0000000001, # 11 = 0x0001
    "blue":     0b0000000010, # 12 = 0x0002
    "green":    0b0000100100, # 13+21 = 0x0024
    "yellow":   0b0101001000, # 14+22+31 = 0x0148 (door wired to yellow)
    "red":      0b0010010000, # 15+23 = 0x0090
    "door":     0b0100000000, # 31 = extra 230V "ON AIR" door lamp (flash/blink=on)
    "switch":   0b1000000000, # 32 = extra 230V mains switch (flash/blink ignored)
    "all":      0b0111111111  # all without the 230V switch (we dont want the switch in lamp test)
}
# GREEN =  0b0000100100 # 13+21 = 0x0024
# YELLOW = 0b0001001000 # 14+22 = 0x0048
# RED =    0b0110010000 # 15+23+31 = 0x0190
# BLUE =   0b0000000010 # 12 = 0x0002

# perform a lamp test upon initial start (all lamps on for 3 seconds)
handle_token('all', 'on')
io_write(sig_state)
time.sleep(3.0)
handle_token('all', 'off')
io_write(sig_state)


if __name__ == "__main__":
    run()
