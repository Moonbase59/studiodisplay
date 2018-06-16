#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
colortemperature.py (Python 2)

A simple conversion from Kelvin color temperature to a near RGB equivalent.
Approximation is best between 1,000 and 40,000 °K.

Based on the work of
  - Tenner Helland --> http://www.tannerhelland.com/4435/convert-temperature-rgb-algorithm-code/
  - Neil Bartlett --> https://github.com/neilbartlett/color-temperature

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

# Calculate RGB values from a color temperature in °K
def color_temperature_to_rgb(kelvin):

    temperature = kelvin / 100.0

    # Calculate red
    if temperature < 66.0:
        red = 255
    else:
        # a + b x + c Log[x] /.
        # {a -> 351.97690566805693`,
        #  b -> 0.114206453784165`,
        #  c -> -40.25366309332127
        #  x -> (kelvin/100) - 55}
        red = temperature - 55.0
        red = 351.97690566805693+ 0.114206453784165 * red - 40.25366309332127 * math.log(red)
        if red < 0:
            red = 0
        if red > 255:
            red = 255

    # Calculate green
    if temperature < 66.0:
        # a + b x + c Log[x] /.
        # {a -> -155.25485562709179`,
        # b -> -0.44596950469579133`,
        # c -> 104.49216199393888`,
        # x -> (kelvin/100) - 2}
        green = temperature - 2
        green = -155.25485562709179 - 0.44596950469579133 * green + 104.49216199393888 * math.log(green)
        if green < 0:
            green = 0
        if green > 255:
            green = 255
    else:
        # a + b x + c Log[x] /.
        # {a -> 325.4494125711974`,
        # b -> 0.07943456536662342`,
        # c -> -28.0852963507957`,
        # x -> (kelvin/100) - 50}
        green = temperature - 50.0
        green = 325.4494125711974 + 0.07943456536662342 * green - 28.0852963507957 * math.log(green)
        if green < 0:
            green = 0
        if green > 255:
            green = 255

    # Calculate blue
    if temperature >= 66.0:
        blue = 255
    elif temperature <= 20.0:
        blue = 0
    else:
        # a + b x + c Log[x] /.
        # {a -> -254.76935184120902`,
        # b -> 0.8274096064007395`,
        # c -> 115.67994401066147`,
        # x -> kelvin/100 - 10}
        blue = temperature - 10
        blue = -254.76935184120902 + 0.8274096064007395 * blue + 115.67994401066147 * math.log(blue)
        if blue < 0:
            blue = 0
        if blue > 255:
            blue = 255

    # return r,g,b
    return int(round(red)), int(round(green)), int(round(blue))


# Convert an RGB into a Kelvin color temperature
def rgb_to_color_temperature(r, g, b):
    epsilon = 0.4
    min_temperature = 1000;
    max_temperature = 40000;
    while max_temperature - min_temperature > epsilon:
        temperature = (max_temperature + min_temperature) / 2
        test_r, test_g, test_b = color_temperature_to_rgb(temperature)
        if (test_b / test_r) >= (b / r):
            max_temperature = temperature
        else:
            min_temperature = temperature
    return int(round(temperature))
