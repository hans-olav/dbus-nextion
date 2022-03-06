from dbus_next.aio import MessageBus
from dbus_next.constants import BusType
import sys
import time
import logging
import asyncio
import json
from nextion import Nextion, EventType
from datetime import datetime
from asyncio_mqtt import Client

class TempMapping:
    def __init__(self, lcd_name, has_minmax, has_summary):
        self.lcd_name = lcd_name
        self.has_minmax = has_minmax
        self.has_summary = has_summary

class DbusNextion:
    """Main class"""
    def __init__(self):
        self._display = Nextion('/dev/ttyS0', 9600, self._display_event)
        self._temphum_mappings = {
            'fridge':  TempMapping('Rfg',     False, False),
            'storage': TempMapping('Storage', False, False),
            'inside':  TempMapping('In',      True,  True),
            'outside': TempMapping('Out',     True,  True) }

    async def start(self):
        """Connects to the display, populates initial data and hooks up callbacks."""

        await self._display.connect()
        asyncio.create_task(self._update_time())
        asyncio.create_task(self._mqtt_consumer())

        self._bus = await MessageBus(bus_type=BusType.SYSTEM).connect()

        # Get dbus objects.
        bat_introspect = await self._bus.introspect('com.victronenergy.battery.ttyUSB0', '/')
        roof_introspect = await self._bus.introspect('com.victronenergy.solarcharger.ttyUSB1', '/')
        ground_introspect = await self._bus.introspect('com.victronenergy.solarcharger.ttyUSB2', '/')

        bat_item = self._bus.get_proxy_object('com.victronenergy.battery.ttyUSB0', '/', bat_introspect).get_interface('com.victronenergy.BusItem')
        roof_item = self._bus.get_proxy_object('com.victronenergy.solarcharger.ttyUSB1', '/', roof_introspect).get_interface('com.victronenergy.BusItem')
        ground_item = self._bus.get_proxy_object('com.victronenergy.solarcharger.ttyUSB2', '/', ground_introspect).get_interface('com.victronenergy.BusItem')

        # Battery monitor
        await self._process_bat_items(await bat_item.call_get_items())
        bat_item.on_items_changed(self._process_bat_items)

        # Solar charger roof
        await self._process_roof_solar(await roof_item.call_get_items())
        roof_item.on_items_changed(self._process_roof_solar)

        # Solar charger ground.
        await self._process_ground_solar(await ground_item.call_get_items())
        ground_item.on_items_changed(self._process_ground_solar)

    async def _process_bat_items(self, items):
        """Processes changes to battery monitor values."""

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

        if '/Dc/0/Temperature' in items:
            await self._display.set('Temps.vaBattTempC.val', int(round(items['/Dc/0/Temperature']['Value'].value * 10)))
            await self._trigger_temp_change()

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

    async def _trigger_temp_change(self):
        """Triggers the timers that convert and populate the temps on the pages."""

        await self._display.set('Summary.tmrLoadTemps.en', 1)
        await self._display.set('Temps.tmrLoadTemps.en', 1)

    async def _process_roof_solar(self, items):
        await self._process_solar_items("Roof", items)

    async def _process_ground_solar(self, items):
        await self._process_solar_items("Ground", items)

    async def _process_solar_items(self, loc, items):
        """Processes changes to solar charger values."""

        if '/Yield/Power' in items:
            await self._display.set(f'Summary.x{loc}Power.val', int(round(items['/Yield/Power']['Value'].value)))
            await self._display.set(f'Electric.x{loc}Power.val', int(round(items['/Yield/Power']['Value'].value)))

        if '/History/Daily/0/Yield' in items:
            await self._display.set(f'Electric.x{loc}Yield.val', int(round(items['/History/Daily/0/Yield']['Value'].value*100)))

        if '/History/Daily/0/MaxPower' in items:
            await self._display.set(f'Electric.x{loc}MaxPwr.val', int(round(items['/History/Daily/0/MaxPower']['Value'].value)))

    async def _mqtt_consumer(self):
        """Update temperatures from Govee sensors published via MQTT."""

        while True:
            try:
                async with Client('localhost') as client:
                    async with client.filtered_messages("temphum/+") as messages:
                        await client.subscribe("temphum/#")
                        async for message in messages:
                            payload = json.loads(message.payload.decode())
                            mapping = self._temphum_mappings.get(message.topic.split('/')[-1])

                            if mapping != None:
                                name = mapping.lcd_name
                                await self._display.set(f'Temps.va{name}TempC.val', int(round(payload['temp']['current'] * 10)))
                                await self._display.set(f'Temps.x{name}Hum.val', int(round(payload['humidity']['current'] * 10)))

                                if mapping.has_minmax:
                                    await self._display.set(f'Temps.va{name}MinTempC.val', int(round(payload['temp']['min'] * 10)))
                                    await self._display.set(f'Temps.va{name}MaxTempC.val', int(round(payload['temp']['max'] * 10)))
                                    await self._display.set(f'Temps.x{name}MinHum.val', int(round(payload['humidity']['min'] * 10)))
                                    await self._display.set(f'Temps.x{name}MaxHum.val', int(round(payload['humidity']['max'] * 10)))

                                if mapping.has_summary:
                                    await self._display.set(f'Summary.x{name}Hum.val', int(round(payload['humidity']['current'] * 10)))

                            await self._trigger_temp_change()
            except MqttError as error:
                print(f'Error "{error}". Reconnecting...')
            finally:
                await asyncio.sleep(reconnect_interval)

    async def _update_time(self):
        """Forever loop that updates the date/time on the display."""

        while True:
            date_str = datetime.now().strftime("%m/%d/%y %H:%M:%S")
            await self._display.set('Summary.txtDateTime.txt', date_str)
            await asyncio.sleep(1 - datetime.now().microsecond/1000000 + 0.05) # Align execution with second boundary.

    async def _display_event(self, type_, data):
        """Display callback. Not doing much for now."""

        if type_ == EventType.STARTUP:
            print('We have booted up!')
        elif type_ == EventType.TOUCH:
            print('A button (id: %d) was touched on page %d' % (data.component_id, data.page_id))

        logging.info('Event %s data: %s', type, str(data))

loop = asyncio.get_event_loop()

async def main():
    """Main method. Set up logging, event loop and start running."""

    logging.basicConfig(
        format='%(asctime)s %(levelname)s - %(message)s',
        level=logging.DEBUG,
        handlers=[
            logging.StreamHandler()
        ])

    handler = DbusNextion()
    await handler.start()
    await loop.create_future()

loop.run_until_complete(main())
