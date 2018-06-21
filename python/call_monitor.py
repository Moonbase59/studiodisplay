#!/usr/bin/env python2
# -*- coding: utf-8 -*-

"""
call_monitor.py (Python 2)

Call monitor for AVM Fritz!Box routers (port 1012, must be enabled).

Original copyright notice:

    py-fritz-monitor
    Version 1.0.1

    The folowing code is written in Python 3.
    Original work by http://www.blog.smartnoob.de
    If you find bugs or you have any question, please inform me via GitHub
    https://github.com/HcDevel/py-fritz-monitor

Modified not to eat 100% CPU, blocking .listen().

Copyright modifications © 2018 Matthias C. Hormann (@Moonbase59, mhormann@gmx.de)
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


from __future__ import print_function
import socket
import select
import threading
import contextlib
import time
import datetime

class callmonitor:
    def __init__(self, hostname="fritz.box", port=1012):
        self.hostname = hostname
        self.port = port
        self.connection = None
        self.call_handler = {}
        self.callback = None

    def register_callback(self, function_name=-1):
        if (function_name != -1):
            self.callback = function_name
        else:
            self.callback = None

    def call_callback(self, id, action, details):
        if (self.callback != None):
                self.callback(self, id, action, details)

    def connect (self):
        self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.connection.connect((self.hostname, self.port))
            print("Success connecting to", self.hostname,"on port:",str(self.port))
            return True
            # threading.Thread(target=self.listen).start()
            # let user call listen() ...
        except socket.error as e:
            self.connection = None
            print("Cannot connect to", self.hostname,"on port:",str(self.port),"\nError:",e)
            return False

    def disconnect (self):
        self.listen_running = False
        self.connection.shutdown(2)
        self.connection.close()

    # def listen(self, recv_buffer=4096):
    #     self.listen_running = True
    #     buffer = ""
    #     data = True
    #     while (self.listen_running == True):
    #         data = self.connection.recv(recv_buffer)
    #         buffer += data.decode("utf-8")
    #
    #         while buffer.find("\n") != -1:
    #             line, buffer = buffer.split("\n", 1)
    #             self.parse (line)
    #
    #         time.sleep(1)
    #     return

    def listen(self):
        print ("Listening for calls")
        self.listen_running = True
        with contextlib.closing(self.connection.makefile(mode='rU', bufsize=4096)) as f:
            while (self.listen_running == True):
                l = f.readline()
                self.parse(l)
        return

    def parse(self, line):
        line = line.split(";")
        timestamp = time.mktime(datetime.datetime.strptime((line[0]), "%d.%m.%y %H:%M:%S").timetuple())
        if (line[1] == "RING"):
            self.call_handler[int(line[2])] = {"type": "incoming", "from": line[3], "to": line[4], "device": line[5], "initiated": timestamp, "accepted": None, "closed": None}
            self.call_callback(int(line[2]), "incoming", self.call_handler[int(line[2])])
        elif (line[1] == "CALL"):
            self.call_handler[int(line[2])] = {"type": "outgoing", "from": line[4], "to": line[5], "device": line[6], "initiated": timestamp, "accepted": None, "closed": None}
            self.call_callback(int(line[2]), "outgoing", self.call_handler[int(line[2])])
        elif (line[1] == "CONNECT"):
            self.call_handler[int(line[2])]["accepted"] = timestamp
            self.call_callback(int(line[2]), "accepted", self.call_handler[int(line[2])])
        elif (line[1] == "DISCONNECT"):
            self.call_handler[int(line[2])]["closed"] = timestamp
            self.call_callback(int(line[2]), "closed", self.call_handler[int(line[2])])
