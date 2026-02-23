import time
import serial
if __name__ == "_serial_":
    from __init__ import device
else:
    from ups import device

class deviceSerial(device): # base class for serial communication (RS232)
    def __init__(self, logDetail: int, device_path: str, baud_rate: int, **kwargs):
        super().__init__(logDetail = logDetail, **kwargs)

        if device_path != "SIMULATOR":
            self.scc = serial.Serial(device_path, baud_rate, timeout=1)

    def __del__(self):
        if hasattr(self, 'scc'):
            self.scc.close()

    def resetSerial(self):
        if hasattr(self, 'scc'):
            self.scc.reset_input_buffer()
            self.scc.reset_output_buffer()

    def reopenSerial(self):
        if hasattr(self, 'scc'):
            self.scc.close()
            time.sleep(1)
            self.scc.open()
            time.sleep(1)

    def readSerial(self, cmd: str):
        if hasattr(self, 'scc'): # read data from serial device
            self.resetSerial()
            self.scc.write(bytes.fromhex(cmd))
            self.scc.flush()
            r = self.scc.readline()
            self.resetSerial()     
        else: # enter values manually for debug and test purposes
            r = input(f"Enter message for {bytes.fromhex(cmd[:-6]).decode('utf-8')}: ").encode('utf-8')
            #todo: convert from hex if needed
        return r
