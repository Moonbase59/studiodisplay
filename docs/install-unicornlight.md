# Install UnicornLight

_TODO: Supply more information_

UnicornLight is an experimental mini »ambient light« (Raspberry Pi Zero W or better and [_Unicorn pHAT_](https://shop.pimoroni.com/products/unicorn-phat) or [_Unicorn HAT_](https://shop.pimoroni.com/products/unicorn-hat) required). It can get its light color information from nearly any MQTT topic, as comma-separated RGB or Kelvin value.

Install on a Raspberry Pi Zero W or better as described in [docs/install-signalpi.md](install-signalpi.md#installing-on-a-separate-pi-zero-w) but instead of the _blinkt!_ library install the [Unicorn HAT Python library](https://github.com/pimoroni/unicorn-hat).

The module to call and/or put into crontab is `~/studiodisplay/python/mqtt-unicornlight.py`.
