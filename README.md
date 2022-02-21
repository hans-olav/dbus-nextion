# dbus-nextion
Simple python script to listen to dbus messages from [Victron Energy](https://www.victronenergy.com/) and update a [Nextion](https://nextion.tech/) LCD serial display.

The display takes about 40 mA @ 5V = 0.2 W. It's run by a [Raspberry Pi Zero 2 W](https://www.raspberrypi.com/products/raspberry-pi-zero-2-w/) running Raspian Lite and the Victron Debian packages. The Rasperry Pi consumes about 0.8 W, so the whole setup is about 1 W!

![Screenshot](/screenshot.png)

