import platform
import time
import minimalmodbus
if __name__ == "_modbus_":
    from __init__ import device
else:
    from ups import device

class deviceModbus(device): # base class for modbus communication (USB)
    def __init__(self, logDetail: int, device_path: str, device_id: int, baud_rate: int, **kwargs):
        super().__init__(logDetail = logDetail, **kwargs)
        if platform.system() == "Linux": # switch it off when running on non-linux system for debug and test purposes
            self.scc = minimalmodbus.Instrument(device_path, device_id)
            self.scc.serial.baudrate = baud_rate
            self.scc.serial.timeout = 0.5
            self.scc.debug = logDetail >= 3
        else:
            print(f"Debugging at {platform.system()}")

    def __del__(self):
        if hasattr(self, 'scc'):
            self.scc.serial.close()

    def readRegister(self, register: int, length: int):
        if hasattr(self, 'scc'): # read data from USB device
            time.sleep(0.1) # let interface to calm down
            try:
                r = self.scc.read_registers(register, length)
            except:
                time.sleep(1) # wait a while and try to read once more
                r =  self.scc.read_registers(register, length) # 2nd attempt, here might be error with indent for no reason
        else: # enter values manually for debug and test purposes
            r = input(f"Enter message for {register}: ").encode('utf-8')
        return r

    def writeRegister(self, register: int, value: int):
        if hasattr(self, 'scc'): # read data from USB device
            time.sleep(0.1) # just in case, let interface calm down
            try:
                self.scc.write_register(register, value)
                return True
            except:
                time.sleep(1) # wait a while and try to read once more
                self.scc.write_register(register, value)
                return True
        else:
            print(f'write register {register} value {value}')
            return True
