#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
icymonitor.py (Python 3)

Attempt to read a radio stream title from the actual stream.
This should work for Shoutcast (1.x & 2.x) and Icecast servers.

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

import urllib.request
import contextlib
import re
import platform
import time
import chardet # pip3 install chardet

# read won’t stop on broken stream connections otherwise. Sigh.
import socket


# icymonitor return values
OK = False # 0
ERROR = True # 1

# Need to make urllib.request work with "ICY 200 OK" responses
# for older Shoutcast (1.x) servers

def read_status_icy(self):
    class InterceptedHTTPResponse():
        pass
    import io
    line = self.fp.readline().replace(b"ICY 200 OK\r\n", b"HTTP/1.0 200 OK\r\n")
    InterceptedSelf = InterceptedHTTPResponse()
    InterceptedSelf.fp = io.BufferedReader(io.BytesIO(line))
    InterceptedSelf.debuglevel = self.debuglevel
    InterceptedSelf._close_conn = self._close_conn
    return ORIGINAL_HTTP_CLIENT_READ_STATUS(InterceptedSelf)


def icymonitor(url, callback=None, encoding=None, timeout=5.0):

    # reset stopping semaphore
    global stopping
    stopping = False

    # bad style to modify things in an underlying module,
    # but otherwise read will block forever if stream gets broken
    socket.setdefaulttimeout(timeout)

    request = urllib.request.Request(url, headers = {
        'User-Agent': 'StudioDisplay/0.5 (' +
            platform.system() + '; ' +
            platform.release() + '; ' +
            platform.machine() + '; ' +
            platform.architecture()[0] + '; ' +
            (encoding or '') + ')',
        'Icy-MetaData': '1',
        'Range': 'bytes=0-',
        'X-Clacks-Overhead': 'GNU Terry Pratchett'
    })

    try:
        # the connection will be closed on exit from with block
        with contextlib.closing(urllib.request.urlopen(request)) as response:

            code = response.getcode()
            print(code)
            # here we get the (already decoded) ICY/HTTP response header
            header_data = response.info()
            #print(header_data['icy-name'])

            # unfortunately, Shoutcast 2.x and Icecast mess it up and
            # DOUBLE-ENCODE UTF-8 characters, so we must force a second decode
            # (Python3 code. Python2 would use "for k, x in info.iteritems()".)
            info = {}
            for k, v in header_data.items():
                info[k] = v.encode('raw_unicode_escape').decode('utf-8')
            print(info)

            # we cannot guarantee that every icy-header is present, so need to test
            if 'icy-name' in info:
                icy_name = info['icy-name']
            else:
                icy_name = ''

            if 'icy-genre' in info:
                icy_genre = info['icy-genre']
            else:
                icy_genre = ''

            if 'icy-description' in info:
                icy_description = info['icy-description']
            else:
                icy_description = ''

            print(icy_name)
            print(icy_genre)
            print(icy_description)

            # FIXME: Initially, set to something different than a real title (not an empty string)
            # since some stations deliberately send an empty Stream Title
            # and we wouldn’t get an initial callback if the title was empty
            current_title = '—' # use an EM DASH for now (U+2014)
            meta_interval = int(info['icy-metaint'])

            while True:
                # FIXME: check for graceful stop
                if stopping:
                    return OK

                #print "skipping " + str(meta_interval)
                try:
                    response.read(meta_interval) # throw away the data until the meta interval
                except (Exception, socket.timeout) as e:
                    print(e)
                    return ERROR

                # FIXME: check for graceful stop
                if stopping:
                    return OK

                try:
                    length = ord(response.read(1)) * 16 # length is encoded in the stream
                except (Exception, socket.timeout) as e:
                    print(e)
                    return ERROR
                #print "length=" + str(length)
                # metadata is often zero until next song change!
                while length == 0:
                    #print "got nothing …"
                    #print "skipping " + str(meta_interval)

                    # FIXME: check for graceful stop
                    if stopping:
                        return OK

                    try:
                        response.read(meta_interval)
                        length = ord(response.read(1)) * 16 # length is encoded in the stream
                    except (Exception, socket.timeout) as e:
                        print(e)
                        return ERROR

                try:
                    metadata = response.read(length).rstrip(b'\0')
                    #print(metadata)
                except (Exception, socket.timeout) as e:
                    print(e)
                    return ERROR

                stream_title = re.search(br"StreamTitle='(.*?)';", metadata)

                # we want to pass the station name at least once, so we need to
                # differntiate between "not found" (=None) and an empty string
                if stream_title != None:

                    stream_title = stream_title.group(1)

                    # try to detect encoding if none given
                    if not encoding:
                        enc = chardet.detect(stream_title)['encoding']
                        print(enc)
                        print(chardet.detect(stream_title)['confidence'])
                        # not detected (=None)?
                        if not enc:
                            # fall back to utf-8
                            enc = 'utf-8' # should this be 'latin1'?
                    else:
                        enc = encoding

                    stream_title = stream_title.decode(enc, errors='replace')

                    # prevent unneccessary callbacks if title hasn’t changed
                    if current_title != stream_title:
                        current_time = time.time()
                        #print(stream_title)
                        if callback:
                            callback(timestamp=current_time, station=icy_name, genre=icy_genre, description=icy_description, title=stream_title)
                        current_title = stream_title
                    else:
                        pass

                else:
                    #print('No StreamTitle!')
                    pass
    except Exception as e:
        print(e)
        return ERROR

    return OK


# A means of stopping icymonitor (maybe to reload a different stream)
# This can only be called asychronously, like from a thread!
def icymonitor_stop():
    global stopping
    stopping = True
    print("Stopping icymonitor …")
    return


# A sample callback function
def print_title(timestamp, station='', genre='', description='', title=''):

    print('{}: {} - {}'.format(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp)), station, title))
    return


# override urllib.request's _read_status function to also allow "ICY 200 OK"
ORIGINAL_HTTP_CLIENT_READ_STATUS = urllib.request.http.client.HTTPResponse._read_status
urllib.request.http.client.HTTPResponse._read_status = read_status_icy

# semaphore will be set to True by icymonitor_stop to allow graceful shutdown
stopping = False

# Sample usage:

#stream_url = sys.argv[1]
#icymonitor(stream_url, callback=print_title)

#icymonitor("http://streamplus31.leonex.de:35194", callback=print_title, encoding='latin1')
#icymonitor("http://stream.radio-paranoid.de:8000/stream.mp3", callback=print_title, encoding='utf-8')
#icymonitor("http://sc6.radiocaroline.net:8040", callback=print_title)
#icymonitor("http://80.86.85.56:8000", callback=print_title)
