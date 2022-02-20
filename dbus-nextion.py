import sys
import time
import dbus
import logging
import Adafruit_SSD1306

from PIL import Image, ImageDraw, ImageFont

class DbusDisplay:
    def __init__(self):
        self._conn = dbus.SystemBus()

        self._oled = Adafruit_SSD1306.SSD1306_128_64(rst=None)
        self._oled.begin()

        self._oled.clear()
        self._oled.display()
        self._image = Image.new("1", (self._oled.width, self._oled.height))

        # Get drawing object to draw on image.
        self._draw = ImageDraw.Draw(self._image)
        self._font = ImageFont.truetype('/home/pi/windows_command_prompt.ttf', 16)

        self._top = -2

    def loop(self):
        while True:
            try:
                # Draw a black filled box to clear the image.
                self._draw.rectangle((0, 0, self._oled.width, self._oled.height), outline=0, fill=0)

                self._draw_electrics()
                self._oled.image(self._image)
                self._oled.set_contrast(50)

                self._oled.display()

                #self._draw.rectangle((0,0,width,height), outline=0, fill=0)
                #self._draw_temps(draw)
                #self._oled.image(image)
                #self._oled.display()

            except KeyboardInterrupt:
                sys.exit()
            except:
                logging.exception('Main loop exception.')

            time.sleep(.5)

    def _draw_electrics(self):
        # Get stats from Dbus
        watts = self._get_dbus_value('com.victronenergy.battery.ttyUSB0', '/Dc/0/Power')
        amps = self._get_dbus_value('com.victronenergy.battery.ttyUSB0', '/Dc/0/Current')
        volts = self._get_dbus_value('com.victronenergy.battery.ttyUSB0', '/Dc/0/Voltage')
        soc = self._get_dbus_value('com.victronenergy.battery.ttyUSB0', '/Soc')
        ah = self._get_dbus_value('com.victronenergy.battery.ttyUSB0', '/ConsumedAmphours')
        secondsLeft = self._get_dbus_value('com.victronenergy.battery.ttyUSB0', '/TimeToGo')
        roof = self._get_dbus_value('com.victronenergy.solarcharger.ttyUSB1', '/Yield/Power')
        ground = self._get_dbus_value('com.victronenergy.solarcharger.ttyUSB2', '/Yield/Power')

        offset = 13
        x = 40
        x2 = x + 4
        y = self._top
        self._draw.text((x,  y), "{:.2f}".format(soc), anchor="ra", font=self._font, fill=255)
        self._draw.text((x2, y), "%", font=self._font, fill=255)

        y += offset
        self._draw.text((x, y), "{:.2f}".format(volts), anchor="ra", font=self._font, fill=255)
        self._draw.text((x2, y), "V", font=self._font, fill=255)

        y += offset
        self._draw.text((x, y), "{:.1f}".format(amps), anchor="ra", font=self._font, fill=255)
        self._draw.text((x2, y), "A", font=self._font, fill=255)

        y += offset
        self._draw.text((x, y), "{:.0f}".format(watts), anchor="ra", font=self._font, fill=255)
        self._draw.text((x2, y), "W", font=self._font, fill=255)

        y += offset
        self._draw.text((x, y), "{:.2f}".format(ah), anchor="ra", font=self._font, fill=255)
        self._draw.text((x2, y), "Ah", font=self._font, fill=255)

        x = 100
        x2 = x + 5
        y = self._top
        self._draw.text((x, y), "Roof", anchor="ma", font=self._font, fill=255)

        y += offset
        self._draw.text((x,  y), "{:.0f}".format(roof), anchor="ra", font=self._font, fill=255)
        self._draw.text((x2, y), "W", font=self._font, fill=255)

        y += offset
        self._draw.text((x, y), "Ground", anchor="ma", font=self._font, fill=255)

        y += offset
        self._draw.text((x, y), "{:.0f}".format(ground), anchor="ra", font=self._font, fill=255)
        self._draw.text((x2, y), "W", font=self._font, fill=255)

        y += (offset + 1)

        s = "-"
        if isinstance(secondsLeft, dbus.Double):
            days, remainder = divmod(secondsLeft, 60*60*24)
            hours, remainder = divmod(remainder, 60*60)
            minutes, remainder = divmod(remainder, 60*60)
            s = "{}.{:02}:{:02}".format(int(days), int(hours), int(minutes))

        self._draw.text((x, y), s, anchor="ma", font=self._font, fill=255)

    def _draw_temps(self):
        offset = 20

        x = 0
        x2 = 60
        x3 = x2 + 5
        x4 = 116
        x5 = x4 + 5
        y = self._top
        self._draw.text((x, y), "In", font=font, fill=255)
        self._draw.text((x2, y), "15.6", anchor="ra", font=font, fill=255)
        self._draw.text((x3, y), "°c", font=font, fill=255)

        self._draw.text((x4, y), "96.8", anchor="ra", font=font, fill=255)
        self._draw.text((x5, y), "%", font=font, fill=255)

        y += offset
        self._draw.text((x, y), "Out", font=font, fill=255)
        self._draw.text((x2, y), "1.6", anchor="ra", font=font, fill=255)
        self._draw.text((x3, y), "°c", font=font, fill=255)

        self._draw.text((x4, y), "48.8", anchor="ra", font=font, fill=255)
        self._draw.text((x5, y), "%", font=font, fill=255)

        y += offset
        self._draw.text((x, y), "Rfg", font=font, fill=255)
        self._draw.text((x2, y), "4.6", anchor="ra", font=font, fill=255)
        self._draw.text((x3, y), "°c", font=font, fill=255)

        self._draw.text((x4, y), "60.8", anchor="ra", font=font, fill=255)
        self._draw.text((x5, y), "%", font=font, fill=255)

    def _get_dbus_value(self, service, path):
        return self._conn.call_blocking(service, path, None, 'GetValue', '', [])

def main():
    display = DbusDisplay()
    display.loop()

if __name__ == '__main__':
    main()
