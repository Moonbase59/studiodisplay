# Translation (i18n, l10n)

StudioStatus and StudioDisplay are utterly, completely translateable.

Both the web client (via Javascript) and the Python modules use *the same language files*. This makes it easy to translate the whole system consistently.

We use JSON data, since it is most easily parseable by any modern language like Javascript, Java, Python, PHP and so forth. Also, for a small project like this, it doesn’t have the complexity of `.po` files. Syntax (and internal usage) are still pretty much *gettext*-like.

Language files are stored in the `config/` folder and use HTML/Javascript-type ISO locale names:

Language file | Language
--- | ---
lang-en-US.json | English as spoken in the U.S.
lang-en-GB.json | English as spoken in Great Britain
lang-de-DE.json | German as spoken in Germany


## Help needed!

Such a versatile und highly usable modular system as this should be available to many more users—in their native language!

**So please help if you can!**

Any language helps, but currently we’re especially interested in these:

| Missing languages |
| --- |
| French |
| Spanish |
| Dutch |
| Danish |
| Russian |

It’d be a bonus if you know the correct meteorological terms and the official measurement units for your language and country.

Ideally, fork the project on Github, install it, create your own language file based on `lang-en-US.json`, add it and make a pull request.

If that’s too complicated, you can also open an issue and attach your language file, or send it to me via email.


## Translation rules

If you know the *gettext* plural rules for your country and language, please put these at the top of the file.

Always start out with either the `lang-en-US.json` or the `lang-en-GB` language file. Make a copy and name it according to the HTML/Javascript ISO language codes, first the language, then a dash, then the country.

French as spoken in France would thus become
```
lang-fr-FR.json
```
while French as spoken in, say, French Polynesia would become
```
lang-fr-PF.json
```

For starters, you can use the W3Schools lists as a reference:

* [ISO Language Codes](https://www.w3schools.com/tags/ref_language_codes.asp)
* [ISO Country Codes](https://www.w3schools.com/tags/ref_country_codes.asp)

Next, **never change the left part of a translation entry!** This would make it unusable because the translation routines then cannot find the original text anymore.

So, if you get
```json
"Incoming call": "Incoming call",
```
just don’t ever touch the left part (before the colon) but instead translate the right part *only*:
```json
"Incoming call": "Appel entrant",
```

No extra characters or comments are allowed in a translation file! So each of the four lines below is considered illegal and will cause an error:

```json
; a comment line
"Incoming call": "Incoming call", ; incoming call message
# a comment line
"Incoming call": "Incoming call", # incoming call message
```

You *can* use an empty line to visually separate blocks, though (like we do).

## Unit conversion

Throughout the internal MQTT bus, metric units (SI units) are used. These get translated at the endpoints, which makes the system extremely robust and flexible.

The web client features an internal unit converter (in `studiodisplay.js`) that can, for instance, translate temperatures from °C to °F, pressures from hPa to mbar, or inHg (inches Hg) even.

The best is that you can use the language files to specify which units you want. They use a special syntax (which is not supposed to occur in regular text), so you can easily adapt everything to your personal preferences.

Here’s an example, for US English:

```json
{
  "": {
    "language": "en-US",
    "plural-forms": "nplurals=2; plural=(n!=1) ? 1 : 0;"
  },
  ".temperature": "F",
  ".temperature_text": "°F",
  ".speed": "mph",
  ".speed_text": "mph",
  ".speed_decimals": "1",
  ".pressure": "mbar",
  ".pressure_text": "mbar",
  ".pressure_decimals": "0",
  ".precipitation": "in",
  ".precipitation_text": "in",
  ".precipitation_decimals": "2",
  ".snowfall": "in",
  ".snowfall_text": "in",
  ".snowfall_decimals": "1",
  ".elevation": "ft",
  ".elevation_text": "ft",
}
```

We always keep these at the top of the language files, for easy reference.

Here is a table of units you could use:

Measurement | Unit names | Explanation | Selectable precision
--- | --- | --- | ---
Temperature | C, F, K | degrees Celsius, Fahrenheit, Kelvin | no
Speed | km/h, mph, m/s | kilometers/miles per hour, meters/second | yes
Pressure | hPa, mbar, mmHg, inHg, bar, Pa | hectopascal, millibar, mm mercury, inches mercury, bar, Pascal | yes
Precipitation | mm, in | millimeters, inches | yes
Snowfall | cm, in | centimeters, inches | yes
Elevation | m, ft | meters, feet | no


If we now wanted to change the barometer pressure in the above excerpt to, say, inches of mercury, we’d have to change three values:

```json
".pressure": "mbar",
```

This is the *internal* name of the unit, and it’s used by the unit converter. For inches of mercury, we would use:

```json
".pressure": "inHg",
```

The next one is the *text* that is output in the GUI:

```json
".pressure_text": "mbar",
```

In theory, this could be almost anything, like "inches of mercury", but then again, screen estate is rare, so we’d better use

```json
".pressure_text": "inHg",
```
or maybe
```json
".pressure_text": "in Hg",
```

Now inches is a much larger length unit than, say, millimeters. If we’d display anything with the same number of decimals, the values would often be unusable. This is why some of the units have an extra `_decimals` entry:

```json
".pressure_decimals": "0",
```

For millimeters, millibars or even hectopascals, we’d surely use no decimal places ("0"), but for our desired *inches* of mercury it makes sense to display one decimal:

```json
".pressure_decimals": "1",
```

*Note: Numbers must also be enclosed in quotes!*

All these three now make up the new pressure units entry for the en-US locale:

```json
".pressure": "inHg",
".pressure_text": "in Hg",
".pressure_decimals": "1",
```

Save the file and try it out by setting your webclient locale to **en-US** in the configuration file.

Easy, isn’t it? The StudioStatus system will do all the hard work for you—automagically!

*N.B.: For an official translation, please adhere to the official rules your country uses! In the U.K., for instance, we are used to 'feet' but still use official 'metres' in meteorological data.*
