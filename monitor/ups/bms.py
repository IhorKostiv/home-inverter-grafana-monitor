#import json
import time
import minimalmodbus
from datetime import datetime

class bms(object):
    def __init__(self, isDebug: bool):
        self.isDebug: bool = isDebug

        self.bCurrent: float = 0.0
        self.bVoltage: float = 0.0
        self.bSOC: int = 0
        self.bSOH: int = 0
        self.bRemain: float = 0.0
        self.bFullCapacity: int = 0
        self.bDesignCapacity: int = 0
        self.bCycles: int = 0
        self.bWarning: str = ""
        self.bProtection: str = ""
        self.bFaults: str = ""
        self.bStatus: str = ""
        self.bBalance: str = ""
        self.bVoltages = {}
        self.bTemperatures = {}
        self.bMOSFETtemperature: float = 0.0
        self.bEnvironmentTemperature: float = 0.0
    def addNotEmpty(self, f: dict, key: str, e:any): # add only not empty values to json in order to save memory and bandwith
        if hasattr(self, key):
            v = getattr(self, key)
            if v != e:
                if isinstance(v, list):
                    i = 1
                    for vv in v:
                        f[key + str(i)] = vv
                        i += 1
                    # f[key] = json.dumps(v)
                else:
                    f[key] = v
    def jSON(self, uKey: str) -> str:
        f = { # must have fields
            "bCurrent": self.bCurrent,
            "bVoltage": self.bVoltage, 
            "bSOC": self.bSOC,
            "bRemain": self.bRemain,
            "bCycles": self.bCycles,
        }
        optionalValues = [ # optional fields to save space and traffic
            ("bSOH", 0),
            ("bFullCapacity", 0),
            ("bDesignCapacity", 0),
            ("bWarning", ''),
            ("bProtection", ''),
            ("bFaults", ''),
            ("bStatus", ''),
            ("bBalance", ''),
            ("bVoltages", []),
            ("bTemperatures", []),
            ("bMOSFETtemperature", 0),
            ("bEnvironmentTemperature", 0)
        ]
        for key, value in optionalValues:
            self.addNotEmpty(f, key, value)

        return [
            {
                "measurement": "bms",
                "tags": { "uKey": uKey },
                "fields": f
            }
        ]

class bmsModbus(bms): # base class for modbus communication (USB)
    def __init__(self, isDebug: bool, device_path: str, device_id: int, baud_rate: int):
        super().__init__(isDebug)

        if device_path != "SIMULATOR":
            self.scc = minimalmodbus.Instrument(device_path, device_id)
            self.scc.serial.baudrate = baud_rate
            self.scc.serial.timeout = 0.5
            self.scc.debug = isDebug
    def __del__(self):
        if hasattr(self, 'scc'):
            self.scc.serial.close()
    def readRegister(self, register: int, length: int):
        if hasattr(self, 'scc'): # read data from USB device
            time.sleep(0.02) # let interface to calm down
            try:
                r = self.scc.read_registers(register, length)
            except:
                time.sleep(10) # wait a while and try to read once more
                r =  self.scc.read_registers(register, length) # 2nd attempt, here might be error with indent for no reason
        else: # enter values manually for debug and test purposes
            r = input(f"Enter message for {register}: ").encode('utf-8')
        return r
    def writeRegister(self, register: int, value: int):
        if hasattr(self, 'scc'): # write data to USB device
            time.sleep(0.1) # just in case, let interface calm down
            try:
                return self.scc.write_register(register, value)
            except:
                time.sleep(1) # wait a while and try to read once more
                return self.scc.write_register(register, value)
        else:
            print(f'write register {register} value {value}')
            return

def addText(t1:str, t2: str, Delimiter: bool = True): # used to concatenate strings in warning and error messages to add comma separation where needed
    return t1 + (", " if Delimiter else "") + t2 if t1 != "" else t2

def bitmaskText(newLine, Bitmask, Texts, Delimiter: bool = True): # used to convert error or warning bitmasks to text
    t = ""
    for b in Texts:
        if b & Bitmask == b:
            t = addText(t, Texts[b], Delimiter)
    return ", " + t if newLine and t != "" else t

def bitmaskNegative(value): # used to extract battery power and current values
    if value > 32768:
        return value - 65536
    else:
        return value

class MUST(bmsModbus): #  object to communicate with and manage MUST battery
    def __init__(self, isDebug: bool, device_path: str):
        super().__init__(isDebug, device_path, 1, 9600)

        self.readData()
    def readRegister(self, register: int, length: int, debugMessage: str):
        if hasattr(self, 'scc'): # check if we are live in production or unit testing
            r = super().readRegister(register, length)
            #if self.isDebug:
            print(f"{datetime.now().strftime('%Y-%m-%d %H:%M')} {debugMessage}: {r}")
        else:
            if register in utMessages:
                r = utMessages[register]
            else:
                r = utRead(register)
        return r
    def readData(self): # read inverter control message values
        bWarnings = {
            1: "battery cell overvoltage alarm",
            2: "battery cell low voltage alarm",
            4: "battery pack overvoltage alarm",
            8: "battery pack low voltage alarm",
            16: "charging over current alarm",
            32: "discharging over current alarm",
            64: "Unknown Warning 6",
            128: "Unknown Warning 7",
            256: "charging high temperature alarm",
            512: "discharging high temperature alarm",
            1024: "charging low temperature alarm",
            2048: "discharging low temperature alarm",
            4096: "environment high temperature alarm",
            8192: "environment low temperature alarm",
            16384: "MOSFET high temperature alarm",
            32768: "SOC Low alarm"
            }
        bProtections = {
            1: "battery cell over voltage protection",
            2: "battery cell low voltage protection",
            4: "battery pack over voltage protection",
            8: "battery pack low voltage protection",
            16: "charging over current protection",
            32: "discharging over current protection",
            64: "short circuit protection",
            128: "charger overvoltage protection",
            256: "charging high temperature protection",
            512: "discharging high temperature protection",
            1024: "charging low temperature protection",
            2048: "discharging low temperature protection",
            4096: "MOSFET high temperature protection",
            8192: "environment high temperature protection",
            16384: "environment low temperature protection",
            32768: "unknown protection 15"
            }
        bFaults = {
            1: "1: charging MOSFET fault",
            2: "1: discharging MOSFET fault",
            4: "1: temperature sensor fault",
            8: "unknown fault 3",
            16: "1: battery cell fault",
            32: "1: front end sampling communication fault",
            64: "unknown fault 6",
            128: "unknown fault 7"
            }
        bStatuses = {
            256: "+",
            512: "-",
            1024: "C", # "charging MOSFET is ON",
            2048: "D", # "discharging MOSFET is ON",
            4096: "L", # "charging Limiter is ON",
            8192: "U",
            16384: "I", # "charger inversed",
            32768: "H" # "heater is ON"
            }
        bBalances = {
            1: "1",
            2: "2",
            4: "3",
            8: "4",
            16: "5",
            32: "6",
            64: "7",
            128: "8",
            256: "9",
            512: "A",
            1024: "B",
            2048: "C",
            4096: "D",
            8192: "E",
            16384: "F",
            32768: "G"
            }

        b = self.readRegister(0, 37, "b")
        self.bCurrent = bitmaskNegative(b[0]) / 100      # 0000 Current 2byte R/INT16 10mA Positive: charging Negative: discharging 
        self.bVoltage = b[1] / 100      # 0001 Voltage of pack 2byte R/UINT16 10mV  
        self.bSOC = b[2]                # 0002 SOC 2byte R/UINT8 % 0~100% 
        self.bSOH = b[3]                # 0003 SOH 2byte R/UINT8 % 0~100% 
        self.bRemain = b[4] / 100       # 0004 Remain capacity 2byte R/UINT16 10mAH  
        self.bFullCapacity = int(b[5] / 100) # 0005 Full capacity 2byte R/UINT16 10mAH  
        self.bDesignCapacity = int(b[6] / 100) # 0006 Design capacity 2byte R/UINT16 10mAH  
        self.bCycles = b[7]             # 0007 Battery cycle counts 2byte R/UINT16 Cyc.  
                                        # 0008 - - - - Reserved 
        self.bWarning = bitmaskText(False, b[9], bWarnings)         # 0009 Warning flag 2byte R/UINT16 Hex See description-1 
        self.bProtection = bitmaskText(False, b[10], bProtections)  # 0010 Protection flag 2byte R/UINT16 Hex See description-2 
        self.bFaults = bitmaskText(False, b[11], bFaults)           # 0011 Status/Fault flag 2byte R/UINT16 Hex See description-3 
        self.bStatus = bitmaskText(False, b[11], bStatuses, False)         
        self.bBalance = bitmaskText(False, b[12], bBalances, False) # 0012 Balance status 2byte R/UINT16 Hex  
                                        # 0013-0014 - - - - Reserved 
        self.bVoltages = []
        for i in range(15, 30):         # 0015-0030 Cell voltage 32byte R/UINT16 mV, Voltage of 16 cells, 2 byte for each cell 
            if b[i] != 65535:
                self.bVoltages += [b[i]/1000]
        self.bTemperatures = []
        for i in range(31, 34):         # 0031-0034 Cell temperature 8byte R/INT16 0.1℃, 4 cell temperature, 2 byte for each cell 
            if b[i] != 65535:
                self.bTemperatures += [bitmaskNegative(b[i])/10]
        self.bMOSFETtemperature = bitmaskNegative(b[35])/10      # 0035 MOSFET temperature 2byte R/INT16 0.1℃ Or invalid 
        self.bEnvironmentTemperature = bitmaskNegative(b[36])/10 # 0036 Environment temperature 2byte R/INT16 0.1℃ Or invalid
        return b

'''# unit test section
def utRead(register: int): # ask for inverter response from console
    r = input(f"Enter message for {register}: ").encode('utf-8')
    return r
'''
# Example usage
if __name__ == "__main__": # testing and debugging
    utMessages = {
        0: [65178, 2652, 98, 100, 19633, 20000, 20000, 4, 65535, 0, 0, 3584, 0, 65535, 65535, 3311, 3311, 3311, 3310, 3309, 3311, 3311, 3310, 65535, 65535, 65535, 65535, 65535, 65535, 65535, 65535, 240, 242, 65535, 65535, 247, 271]
        }

    b: bms = MUST(True, "SIMULATOR")
    print(b.jSON("MUST"))