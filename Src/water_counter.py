from machine import Pin, I2C
from mqtt_as import MQTTClient, config
from ssd1306 import SSD1306_I2C
from utime import ticks_ms, ticks_diff, sleep_ms
from micropython import const
import uasyncio as asyncio
import network
import gc
import ustruct

from counter import Counter
from eeprom import EEPROMValue

i2c = I2C(freq=400000, scl=Pin(5), sda=Pin(4))

#####################################
# Constants and configuration
#####################################


config['keepalive'] = 60
config['clean'] = False
config['will'] = ('/ESP/Wemos/Water/LastWill', 'Goodbye cruel world!', False, 0)

MQTTClient.DEBUG = True

EEPROM_ADDR_HOT_VALUE = const(0)
EEPROM_ADDR_COLD_VALUE = const(4)


#####################################
# Class handles both counters and sends their status to MQTT
#####################################
class CounterMQTTClient(MQTTClient):

    blue_led = Pin(2, Pin.OUT, value = 1)
    button = Pin(0, Pin.IN)

    hot_counter = Counter(12, EEPROMValue(i2c, EEPROM_ADDR_HOT_VALUE))
    cold_counter = Counter(13, EEPROMValue(i2c, EEPROM_ADDR_COLD_VALUE))

    def __init__(self):
        self.internet_outage = True
        self.internet_outages = 0
        self.internet_outage_start = ticks_ms()

        with open("config.txt") as config_file:
            config['ssid'] = config_file.readline().rstrip()
            config['wifi_pw'] = config_file.readline().rstrip()
            config['server'] = config_file.readline().rstrip()
            config['client_id'] = config_file.readline().rstrip()
            self._mqtt_cold_water_theme = config_file.readline().rstrip()
            self._mqtt_hot_water_theme = config_file.readline().rstrip()
            self._mqtt_debug_water_theme = config_file.readline().rstrip()

        config['subs_cb'] = self.mqtt_msg_handler
        config['wifi_coro'] = self.wifi_connection_handler
        config['connect_coro'] = self.mqtt_connection_handler
        config['clean'] = False
        config['clean_init'] = False
        super().__init__(config)

        loop = asyncio.get_event_loop()
        loop.create_task(self._heartbeat())
        loop.create_task(self._counter_coro(self.cold_counter, self._mqtt_cold_water_theme))
        loop.create_task(self._counter_coro(self.hot_counter, self._mqtt_hot_water_theme))
        loop.create_task(self._display_coro())


    async def _counter_coro(self, counter, topic):
        # Publish initial value
        value = counter.value()
        await self.publish(topic, str(value))

        # Publish each new value
        while True:
            value = await counter
            await self.publish_msg(topic, str(value))


    async def wifi_connection_handler(self, state):
        self.internet_outage = not state
        if state:
            self.dprint('WiFi is up.')
            duration = ticks_diff(ticks_ms(), self.internet_outage_start) // 1000
            await self.publish_debug_msg('ReconnectedAfter', duration)
        else:
            self.internet_outages += 1
            self.internet_outage_start = ticks_ms()
            self.dprint('WiFi is down.')
            
        await asyncio.sleep(0)
        

    async def mqtt_connection_handler(self, client):
        await client.subscribe(self._mqtt_cold_water_theme)
        await client.subscribe(self._mqtt_hot_water_theme)


    def mqtt_msg_handler(self, topic, msg):
        topicstr = str(topic, 'utf8')
        self.dprint("Received MQTT message topic={}, msg={}".format(topicstr, msg))
        if topicstr == self._mqtt_cold_water_theme:
            self.cold_counter.set_value(int(msg))
        if topicstr == self._mqtt_hot_water_theme:
            self.hot_counter.set_value(int(msg))


    async def publish_debug_msg(self, subtopic, msg):
        await self.publish_msg("{}/{}".format(self._mqtt_debug_water_theme, subtopic), str(msg))


    # Publish a message if WiFi and broker is up, else discard
    async def publish_msg(self, topic, msg):
        self.dprint("Publishing message on topic {}: {}".format(topic, msg))
        if not self.internet_outage:
            await self.publish(topic, msg)
        else:
            self.dprint("Message was not published - no internet connection")


    # Blink flash LED if WiFi down
    async def _heartbeat(self):
        while True:
            if self.internet_outage:
                self.blue_led(not self.blue_led()) # Fast blinking if no connection
                await asyncio.sleep_ms(200) 
            else:
                self.blue_led(0) # Rare blinking when connected
                await asyncio.sleep_ms(50)
                self.blue_led(1)
                await asyncio.sleep_ms(5000)


    async def _display_coro(self):
        display = SSD1306_I2C(128,32, i2c)
    
        while True:
            display.poweron()
            display.fill(0)
            display.text("COLD: {:.3f}".format(self.cold_counter.value() / 1000), 16, 4)
            display.text("HOT:  {:.3f}".format(self.hot_counter.value() / 1000), 16, 20)
            display.show()
            await asyncio.sleep(3)
            display.poweroff()

            while self.button():
                await asyncio.sleep_ms(20)


    async def _connect_to_WiFi(self):
        self.dprint('Connecting to WiFi and MQTT')
        sta_if = network.WLAN(network.STA_IF)
        sta_if.connect(config['ssid'], config['wifi_pw'])
        
        conn = False
        while not conn:
            await self.connect()
            conn = True

        self.dprint('Connected!')
        self.internet_outage = False


    async def _run_main_loop(self):
        # Loop forever
        mins = 0
        while True:
            gc.collect()  # For RAM stats.
            mem_free = gc.mem_free()
            mem_alloc = gc.mem_alloc()

            try:
                await self.publish_debug_msg("Uptime", mins)
                await self.publish_debug_msg("Repubs", self.REPUB_COUNT)
                await self.publish_debug_msg("Outages", self.internet_outages)
                await self.publish_debug_msg("MemFree", mem_free)
                await self.publish_debug_msg("MemAlloc", mem_alloc)
            except Exception as e:
                self.dprint("Exception occurred: ", e)
            mins += 1

            await asyncio.sleep(60)


    async def main(self):
        while True:
            try:
                await self._connect_to_WiFi()
                await self._run_main_loop()
                    
            except Exception as e:
                self.dprint('Global communication failure: ', e)
                await asyncio.sleep(20)


gc.collect()
client = CounterMQTTClient()
loop = asyncio.get_event_loop()
loop.run_until_complete(client.main())
