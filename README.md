## Water Meter Description

Water Meter device is intended to count pulses on 2 water flow meters (hot and cold water) and then publish counted value to consumers via MQTT protocol. Additionally device displays current values on a SSD1306 based display.

The device is based on ESP8266 module (ESP-07 or ESP-12). 

This github space contains firmware for the device. Additionally you may refer to
* [Board schematic and PCB](https://easyeda.com/editor#id=22b1dc7469f045d1a97160dd76647c4c|1b87dd112b7949cfb40f412b40f98e09)
* [Case 3D model](https://cad.onshape.com/documents/5f3dc0e54cb4b2a42d2d7384/v/9ec48c3fd374e797db5aece7/e/e4a4facc97d991164f090cc5)

## Building the firmware

The firmware is written in [micropython](https://github.com/micropython/micropython). Since ESP8266 module has a very limited amount of RAM some trick are required to reduct RAM consumption.
* Some classes have to be pre-compiled so that ESP8266 executes bytecode (not spending RAM for compilation)
* Library classes have to be burned into the firmware so that so that ESP8266 executes bytecode right from flash (refer to 'frozen bytecode' in micropython documentation)

So the building algorithm will be as follows:
* Build the micropython firmware
  * Download and build [ESP Open SDK](https://github.com/pfalcon/esp-open-sdk)
  * Download [Micropython sources](https://github.com/micropython/micropython)
  * Put 'Libraries' directory contents into Micropython's [ports/esp8266/modules directory](https://github.com/micropython/micropython/tree/master/ports/esp8266/modules)
  * Build Micropython accoring to [ESP8266 port instructions](https://github.com/micropython/micropython/tree/master/ports/esp8266)
  * Flash built firmware into ESP8266 module (e.g. with esptool.py)
* Upload files in 'Src' directory to module internal filesystem
  * Rename config.txt.template to config.txt and fill your configuration parameters inside
  * Pre-compile all .py files with mpy-cross (except for main.py)
  * Upload config.txt, all .mpy files and main.py to the device (e.g. with ampy.py)

## Credits

For build convenience some libraries were copied into this repository. Here is the list of libraries used with the links to origin
- [mqtt_as](https://github.com/peterhinch/micropython-mqtt/tree/master/mqtt_as)
- uasyncio and collections libraries came from [micropython-lib](https://github.com/micropython/micropython-lib)