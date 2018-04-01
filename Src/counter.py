from machine import Pin, I2C
import uasyncio as asyncio
from micropython import const
import ustruct

#####################################
# Counter class - abstracts a single counter
#####################################
class Counter():
    debounce_ms = const(25)
    
    def __init__(self, pin_num, value_storage):
        self._value_storage = value_storage
        
        self._value = self._value_storage.read()
        self._value_changed = False

        self._pin = Pin(pin_num, Pin.IN, Pin.PULL_UP)

        loop = asyncio.get_event_loop()
        loop.create_task(self._switchcheck())  # Thread runs forever


    """ Poll pin and advance value when another litre passed """
    async def _switchcheck(self):
        last_checked_pin_state = self._pin.value()  # Get initial state

        # Poll for a pin change
        while True:
            state = self._pin.value()
            if state != last_checked_pin_state:
                # State has changed: act on it now.
                last_checked_pin_state = state
                if state == 0:
                    self._another_litre_passed()

            # Ignore further state changes until switch has settled
            await asyncio.sleep_ms(Counter.debounce_ms)


    def _another_litre_passed(self):
        self._value += 1
        self._value_changed = True

        self._value_storage.write(self._value)


    def value(self):
        self._value_changed = False
        return self._value


    def set_value(self, value):
        self._value = value
        self._value_changed = False


    def __await__(self):
        while not self._value_changed:
            yield from asyncio.sleep(0)

        return self.value()

    __iter__ = __await__  
