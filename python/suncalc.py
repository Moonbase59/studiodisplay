#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
suncalc.py (Python 3)

Calculate sun/moon position and light phases.
Based on Vladimir Agafonkin’s JavaScript library (https://github.com/mourner/suncalc),
rewritten for Python and modified to add more times
and repair some faulty calculations.
Returns datetime objects.

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

import math
from datetime import datetime, timedelta
import time

INFINITY = float("inf") # math.inf
PI   = 3.141592653589793 # math.pi
sin  = math.sin
cos  = math.cos
tan  = math.tan
asin = math.asin
atan = math.atan2
acos = math.acos
sqrt = math.sqrt
floor = math.floor
isfinite = math.isfinite
rad  = PI / 180.0
dayMs = 1000 * 60 * 60 * 24
J1970 = 2440588
J2000 = 2451545
J0 = 0.0009;

times  = [
    [     6, 'goldenHourEnd',   'goldenHour'      ],
    [  -0.3, 'sunriseEnd',      'sunsetStart'     ],
    [-0.833, 'sunrise',         'sunset'          ],
    [    -4, 'blueHourDawnEnd', 'blueHourDusk'    ],
    [    -6, 'dawn',            'dusk'            ],
    [    -8, 'blueHourDawn',    'blueHourDuskEnd' ],
    [   -12, 'nauticalDawn',    'nauticalDusk'    ],
    [   -18, 'nightEnd',        'night'           ]
]

e = rad * 23.4397 # obliquity of the Earth

def rightAscension(l, b):
    return atan(sin(l) * cos(e) - tan(b) * sin(e), cos(l))

def declination(l, b):
    return asin(sin(b) * cos(e) + cos(b) * sin(e) * sin(l))

def azimuth(H, phi, dec):
    return PI + atan(sin(H), cos(H) * sin(phi) - tan(dec) * cos(phi))

def altitude(H, phi, dec):
    return asin(sin(phi) * sin(dec) + cos(phi) * cos(dec) * cos(H))

def siderealTime(d, lw):
 	return rad * (280.16 + 360.9856235 * d) - lw

def astroRefraction(h):
    # the following formula works for positive altitudes only.
    # if h = -0.08901179 a div/0 would occur
    if h < 0:
        h = 0;
    # formula 16.4 of "Astronomical Algorithms" 2nd edition by Jean Meeus (Willmann-Bell, Richmond) 1998.
    # 1.02 / tan(h + 10.26 / (h + 5.10)) h in degrees, result in arc minutes -> converted to rad:
    return 0.0002967 / tan(h + 0.00312536 / (h + 0.08901179))

def toJulian(date):
    return (time.mktime(date.timetuple()) * 1000) / dayMs - 0.5 + J1970

def fromJulian(j):
    return datetime.fromtimestamp(((j + 0.5 - J1970) * dayMs)/1000.0)

def toDays(date):
 	return toJulian(date) - J2000

def julianCycle(d, lw):
    return round(d - J0 - lw / (2 * PI))

def approxTransit(Ht, lw, n):
    return J0 + (Ht + lw) / (2 * PI) + n

def solarTransitJ(ds, M, L):
    return J2000 + ds + 0.0053 * sin(M) - 0.0069 * sin(2 * L)

def hourAngle(h, phi, d):
    arg = (sin(h) - sin(phi) * sin(d)) / (cos(phi) * cos(d))
    if arg > 1:
        # beyond phi = ± 66.55° no sunset, i.e. 24 hours daylight
        return -INFINITY
    if arg < -1:
        # beyond phi = ± 66.55° no sunrise, i.e. 24 hours darkness
        return INFINITY
    return acos(arg)

def solarMeanAnomaly(d):
    return rad * (357.5291 + 0.98560028 * d)

def eclipticLongitude(M):
    C = rad * (1.9148 * sin(M) + 0.02 * sin(2 * M) + 0.0003 * sin(3 * M)) # equation of center
    P = rad * 102.9372 # perihelion of the Earth
    return M + C + P + PI

def sunCoords(d):
    M = solarMeanAnomaly(d)
    L = eclipticLongitude(M)
    return dict(dec= declination(L, 0),ra= rightAscension(L, 0))

def getSetJ(h, lw, phi, dec, n, M, L):
    w = hourAngle(h, phi, dec)
    if not isfinite(w):
        return w;
    a = approxTransit(w, lw, n)
    return solarTransitJ(a, M, L)

# geocentric ecliptic coordinates of the moon
def moonCoords(d):
    L = rad * (218.316 + 13.176396 * d) # ecliptic longitude
    M = rad * (134.963 + 13.064993 * d) # mean anomaly
    F = rad * (93.272 + 13.229350 * d)  # mean distance

    l  = L + rad * 6.289 * sin(M)   # longitude
    b  = rad * 5.128 * sin(F)       # latitude
    dt = 385001 - 20905 * cos(M)    # distance to the moon in km

    return dict(ra=rightAscension(l, b), dec=declination(l, b), dist=dt)


def getMoonIllumination(date):
    # calculations for illumination parameters of the moon,
    # based on http://idlastro.gsfc.nasa.gov/ftp/pro/astro/mphase.pro formulas and
    # Chapter 48 of "Astronomical Algorithms" 2nd edition by Jean Meeus (Willmann-Bell, Richmond) 1998.

    d = toDays(date)
    s = sunCoords(d)
    m = moonCoords(d)

    # distance from Earth to Sun in km
    sdist = 149598000
    phi = acos(sin(s["dec"]) * sin(m["dec"]) + cos(s["dec"]) * cos(m["dec"]) * cos(s["ra"] - m["ra"]))
    inc = atan(sdist * sin(phi), m["dist"] - sdist * cos(phi))
    angle = atan(cos(s["dec"]) * sin(s["ra"] - m["ra"]), sin(s["dec"]) * cos(m["dec"]) - cos(s["dec"]) * sin(m["dec"]) * cos(s["ra"] - m["ra"]))
    fraction = (1 + cos(inc)) / 2
    phase = 0.5 + 0.5 * inc * (-1 if angle < 0 else 1) / PI
    # moon age (day of moon; 0..27)
    age = int(floor(phase * 100.0 / (100.0 / 28)))

    return dict(fraction=fraction, phase=phase, angle=angle, age=age)

def getSunrise(date, lat, lng):
    ret = getTimes(date, lat, lng)
    return ret["sunrise"]

def getTimes(date, lat, lng):
    lw = rad * -lng
    phi = rad * lat

    d = toDays(date)
    n = julianCycle(d, lw)
    ds = approxTransit(0, lw, n)

    M = solarMeanAnomaly(ds)
    L = eclipticLongitude(M)
    dec = declination(L, 0)

    Jnoon = solarTransitJ(ds, M, L)

    result = dict(
        solarNoon = fromJulian(Jnoon),
        nadir = fromJulian(Jnoon - 0.5)
    )

    for i in range(0, len(times)):
        time = times[i]
        Jset = getSetJ(time[0] * rad, lw, phi, dec, n, M, L)

        if not isfinite(Jset):
            Jnoon = 0

        Jrise = Jnoon - (Jset - Jnoon)

        # return None for all times not applicable (like in polar regions)
        result[time[1]] = fromJulian(Jrise) if isfinite(Jrise) else None
        result[time[2]] = fromJulian(Jset) if isfinite(Jset) else None

    return result

# def fromJulianConstrained(date, j):
#
#     min = date.replace(hour=0,minute=0,second=0,microsecond=0)
#     max = date + timedelta(days=1)
#
#     if not isfinite(j):
#         return min if j < 0 else max
#
#     result = fromJulian(j)
#
#     if result < min:
#         return min
#
#     if result > max:
#         return max
#
#     return result

def hoursLater(date, h):
    return date + timedelta(hours=h)

def getMoonTimes(date, lat, lng):
    t = date.replace(hour=0,minute=0,second=0,microsecond=0)

    hc = 0.133 * rad
    pos = getMoonPosition(t, lat, lng)
    h0 = pos["altitude"] - hc
    rise = 0
    sett = 0
    # go in 2-hour chunks, each time seeing if a 3-point quadratic curve crosses zero (which means rise or set)
    for i in range(1,24,2):
        h1 = getMoonPosition(hoursLater(t, i), lat, lng)["altitude"] - hc
        h2 = getMoonPosition(hoursLater(t, i + 1), lat, lng)["altitude"] - hc

        a = (h0 + h2) / 2 - h1
        b = (h2 - h0) / 2
        xe = -b / (2 * a)
        ye = (a * xe + b) * xe + h1
        d = b * b - 4 * a * h1
        roots = 0

        if d >= 0:
            dx = sqrt(d) / (abs(a) * 2)
            x1 = xe - dx
            x2 = xe + dx
            if abs(x1) <= 1:
                roots += 1
            if abs(x2) <= 1:
                roots += 1
            if x1 < -1:
                x1 = x2

        if roots == 1:
            if h0 < 0:
                rise = i + x1
            else:
                sett = i + x1

        elif roots == 2:
            rise = i + (x2 if ye < 0 else x1)
            sett = i + (x1 if ye < 0 else x2)

        if (rise and sett):
            break

        h0 = h2

    result = dict()

    if (rise):
        result["rise"] = hoursLater(t, rise)
    if (sett):
        result["set"] = hoursLater(t, sett)

    if (not rise and not sett):
        value = 'alwaysUp' if ye > 0 else 'alwaysDown'
        result[value] = True

    return result

def getMoonPosition(date, lat, lng):
    lw  = rad * -lng
    phi = rad * lat
    d   = toDays(date)

    c = moonCoords(d)
    H = siderealTime(d, lw) - c["ra"]
    h = altitude(H, phi, c["dec"])
    # formula 14.1 of "Astronomical Algorithms" 2nd edition by Jean Meeus (Willmann-Bell, Richmond) 1998.
    pa = atan(sin(H), tan(phi) * cos(c["dec"]) - sin(c["dec"]) * cos(H))

    # altitude correction for refraction
    h = h + astroRefraction(h)

    return dict(azimuth=azimuth(H, phi, c["dec"]), altitude=h, distance=c["dist"], parallacticAngle=pa)

def getPosition(date, lat, lng):
    lw  = rad * -lng
    phi = rad * lat
    d   = toDays(date)

    c  = sunCoords(d)
    H  = siderealTime(d, lw) - c["ra"]
    # print("d", d, "c",c,"H",H,"phi", phi)
    return dict(azimuth=azimuth(H, phi, c["dec"]), altitude=altitude(H, phi, c["dec"]))
