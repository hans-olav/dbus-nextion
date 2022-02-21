from dbus_next.aio import MessageBus
from dbus_next.constants import BusType
import sys
import time
import logging
import asyncio
from nextion import Nextion, EventType
from datetime import datetime

class DbusNextion:
    def __init__(self):
        self._display = Nextion('/dev/ttyS0', 9600, self._display_event)

    async def start(self):
        await self._display.connect()
        self._timer = asyncio.create_task(self._update_time())

        self._bus = await MessageBus(bus_type=BusType.SYSTEM).connect()

        bat_introspect = await self._bus.introspect('com.victronenergy.battery.ttyUSB0', '/')
        roof_introspect = await self._bus.introspect('com.victronenergy.solarcharger.ttyUSB1', '/')
        ground_introspect = await self._bus.introspect('com.victronenergy.solarcharger.ttyUSB2', '/')

        bat_item = self._bus.get_proxy_object('com.victronenergy.battery.ttyUSB0', '/', bat_introspect).get_interface('com.victronenergy.BusItem')
        roof_item = self._bus.get_proxy_object('com.victronenergy.solarcharger.ttyUSB1', '/', roof_introspect).get_interface('com.victronenergy.BusItem')
        ground_item = self._bus.get_proxy_object('com.victronenergy.solarcharger.ttyUSB2', '/', ground_introspect).get_interface('com.victronenergy.BusItem')

        await self._process_bat_items(await bat_item.call_get_items())
        bat_item.on_items_changed(self._process_bat_items)

        await self._process_roof_solar(await roof_item.call_get_items())
        roof_item.on_items_changed(self._process_roof_solar)

        await self._process_ground_solar(await ground_item.call_get_items())
        ground_item.on_items_changed(self._process_ground_solar)

    async def _process_bat_items(self, items):
        if '/Dc/0/Power' in items:
            await self._display.set('Summary.xPower.val', int(round(items['/Dc/0/Power']['Value'].value * 10)))
            await self._display.set('Electric.xPower.val', int(round(items['/Dc/0/Power']['Value'].value * 10)))

        if '/Soc' in items:
            await self._display.set('Summary.xSoc.val', int(round(items['/Soc']['Value'].value * 100)))
            await self._display.set('Electric.xSoc.val', int(round(items['/Soc']['Value'].value * 100)))

        if '/Dc/0/Current' in items:
            await self._display.set('Electric.xCurrent.val', int(round(items['/Dc/0/Current']['Value'].value * 10)))

        if '/Dc/0/Voltage' in items:
            await self._display.set('Electric.xVoltage.val', int(round(items['/Dc/0/Voltage']['Value'].value * 100)))

        if '/ConsumedAmphours' in items:
            await self._display.set('Electric.xConsumed.val', int(round(items['/ConsumedAmphours']['Value'].value * 100)))

        if '/TimeToGo' in items:
            val = items['/TimeToGo']['Value']
            s = '-'
            if val.signature == 'd':
                seconds = val.value
                days, remainder = divmod(seconds, 60*60*24)
                hours, remainder = divmod(remainder, 60*60)
                minutes, remainder = divmod(remainder, 60*60)
                s = "{}.{:02}:{:02}".format(int(days), int(hours), int(minutes))
            await self._display.set('Electric.txtTimeLeft.txt', s)

    async def _process_roof_solar(self, items):
        await self._process_solar_items("Roof", items)

    async def _process_ground_solar(self, items):
        await self._process_solar_items("Ground", items)

    async def _process_solar_items(self, loc, items):
#        for k,v in items.items():
 #           print(str(k) + "\t\t" + str(v))
        if '/Yield/Power' in items:
            await self._display.set(f'Summary.x{loc}Power.val', int(round(items['/Yield/Power']['Value'].value)))
            await self._display.set(f'Electric.x{loc}Power.val', int(round(items['/Yield/Power']['Value'].value)))

        if '/History/Daily/0/Yield' in items:
            await self._display.set(f'Electric.x{loc}Yield.val', int(round(items['/History/Daily/0/Yield']['Value'].value*100)))

        if '/History/Daily/0/MaxPower' in items:
            await self._display.set(f'Electric.x{loc}MaxPwr.val', int(round(items['/History/Daily/0/MaxPower']['Value'].value)))

    async def _update_time(self):
        while True:
            date_str = datetime.now().strftime("%m/%d/%y %H:%M:%S")
            await self._display.set('Summary.txtDateTime.txt', date_str)
            await asyncio.sleep(1 - datetime.now().microsecond/1000000 + 0.05)

    async def _display_event(self, type_, data):
        if type_ == EventType.STARTUP:
            print('We have booted up!')
        elif type_ == EventType.TOUCH:
            print('A button (id: %d) was touched on page %d' % (data.component_id, data.page_id))

        logging.info('Event %s data: %s', type, str(data))

loop = asyncio.get_event_loop()

async def main():
    logging.basicConfig(
        format='%(asctime)s - %(levelname)s - %(message)s',
        level=logging.DEBUG,
        handlers=[
            logging.StreamHandler()
        ])

    handler = DbusNextion()
    await handler.start()
    await loop.create_future()

loop.run_until_complete(main())
