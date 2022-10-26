# dbus-nextion
Simple python script to listen to dbus messages from [Victron Energy](https://www.victronenergy.com/) and update a [Nextion](https://nextion.tech/) LCD serial display.

The display takes about 40 mA @ 5V = 0.2 W. It's run by a [Raspberry Pi Zero 2 W](https://www.raspberrypi.com/products/raspberry-pi-zero-2-w/) running Raspian Lite and the Victron Debian packages. The Rasperry Pi consumes about 1.5 W, so the whole setup is less than 2 W with the screen always on!

![Screenshot](/screenshot.png)

This may be required to avoid [this](https://stackoverflow.com/questions/72980064/from-typing-extensions-import-paramspec-importerror-cannot-import-name-paramsp) issue:
```
pip uninstall typing_extensions
pip uninstall fastapi
pip install --no-cache fastapi
```
