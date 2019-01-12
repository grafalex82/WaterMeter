from machine import Pin, I2C
import ustruct

class EEPROM():
    i2c_addr = const(80)

    def __init__(self, i2c):
        self.i2c = i2c
        self.i2c_buf = bytearray(4) # Avoid creation/destruction of the buffer on each call


    def read(self, eeprom_addr):
        try:
            self.i2c.readfrom_mem_into(self.i2c_addr, eeprom_addr, self.i2c_buf, addrsize=8)
        except OSError:
            return 0
        return ustruct.unpack_from("<I", self.i2c_buf)[0]    
        
    
    def write(self, eeprom_addr, value):
        ustruct.pack_into("<I", self.i2c_buf, 0, value)
        try:
            self.i2c.writeto_mem(self.i2c_addr, eeprom_addr, self.i2c_buf, addrsize=8)
        except OSError:
            pass



class EEPROMValue():
    def __init__(self, i2c, eeprom_addr):
        self._eeprom = EEPROM(i2c)
        self._eeprom_addr = eeprom_addr
        

    def read(self):
        return self._eeprom.read(self._eeprom_addr)


    def write(self, value):
        self._eeprom.write(self._eeprom_addr, value)