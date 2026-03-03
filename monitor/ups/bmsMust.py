if __name__ == "__main__":
    from _bms_ import bms
    from _modbus_ import deviceModbus
    from _constants_ import *
else:
    from ups._bms_ import bms
    from ups._modbus_ import deviceModbus
    from ups._constants_ import *

class bmsMUST(bms, deviceModbus): #  object to communicate with and manage MUST battery
    def __init__(self, logDetail: int, device_path: str):
        # bms.__init__(self, logDetail)
        # deviceModbus.__init__(self, logDetail, device_path, 1, 9600)
        super().__init__(logDetail = logDetail, device_path = device_path, device_id = 1, baud_rate = 9600)
        self.uKey = "MUST"
        self.readData()

    def readData(self): # read inverter control message values
        bWarnings = {
            0x0001: "battery cell overvoltage",
            0x0002: "battery cell low voltage",
            0x0004: "battery pack overvoltage",
            0x0008: "battery pack low voltage",
            0x0010: "charging over current",
            0x0020: "discharging over current",
            0x0040: "Unknown Warning 6",
            0x0080: "Unknown Warning 7",
            0x0100: "charging high temperature",
            0x0200: "discharging high temperature",
            0x0400: "charging low temperature",
            0x0800: "discharging low temperature",
            0x1000: "environment high temperature",
            0x2000: "environment low temperature",
            0x4000: "MOSFET high temperature",
            0x8000: "SOC Low"
            }
        bProtections = {
            0x0001: "battery cell over voltage",
            0x0002: "battery cell low voltage",
            0x0004: "battery pack over voltage",
            0x0008: "battery pack low voltage",
            0x0010: "charging over current",
            0x0020: "discharging over current",
            0x0040: "short circuit",
            0x0080: "charger overvoltage",
            0x0100: "charging high temperature",
            0x0200: "discharging high temperature",
            0x0400: "charging low temperature",
            0x0800: "discharging low temperature",
            0x1000: "MOSFET high temperature",
            0x2000: "environment high temperature",
            0x4000: "environment low temperature",
            0x8000: "battery full"
            }
        bFaults = {
            0x01: "charging MOSFET",
            0x02: "discharging MOSFET",
            0x04: "temperature sensor",
            0x08: "unknown fault 3",
            0x10: "battery cell",
            0x20: "front end sampling communication",
            0x40: "unknown fault 6",
            0x80: "unknown fault 7"
            }
        bStatuses = {
            0x0100: "+",
            0x0200: "-",
            0x0400: "C", # "charging MOSFET is ON",
            0x0800: "D", # "discharging MOSFET is ON",
            0x1000: "L", # "charging Limiter is ON",
            0x2000: "U",
            0x4000: "I", # "charger inversed",
            0x8000: "H" # "heater is ON"
            }
        bBalances = {
            0x0001: "1",
            0x0002: "2",
            0x0004: "3",
            0x0008: "4",
            0x0010: "5",
            0x0020: "6",
            0x0040: "7",
            0x0080: "8",
            0x0100: "9",
            0x0200: "A",
            0x0400: "B",
            0x0800: "C",
            0x1000: "D",
            0x2000: "E",
            0x4000: "F",
            0x8000: "G"
            }

        b = self.readRegister(0, 37, "b")
        self.bCurrent = self.signedInt(b[0]) / 100      # 0000 Current 2byte R/INT16 10mA Positive: charging Negative: discharging 
        self.bVoltage = b[1] / 100      # 0001 Voltage of pack 2byte R/UINT16 10mV  
        self.bSOC = b[2]                # 0002 SOC 2byte R/UINT8 % 0~100% 
        self.bSOH = b[3]                # 0003 SOH 2byte R/UINT8 % 0~100% 
        self.bRemain = b[4] / 100       # 0004 Remain capacity 2byte R/UINT16 10mAH  
        self.bFullCapacity = int(b[5] / 100) # 0005 Full capacity 2byte R/UINT16 10mAH  
        self.bDesignCapacity = int(b[6] / 100) # 0006 Design capacity 2byte R/UINT16 10mAH  
        self.bCycles = b[7]             # 0007 Battery cycle counts 2byte R/UINT16 Cyc.  
                                        # 0008 - - - - Reserved 
        self.bWarning = self.bitmaskText(False, b[9], bWarnings)         # 0009 Warning flag 2byte R/UINT16
        self.bProtection = self.bitmaskText(False, b[10], bProtections)  # 0010 Protection flag 2byte R/UINT16
        self.bFaults = self.bitmaskText(False, b[11], bFaults)           # 0011 Status/Fault flag 2byte R/UINT16 
        self.bStatus = self.bitmaskText(False, b[11], bStatuses, '')         
        self.bBalance = self.bitmaskText(False, b[12], bBalances, '')    # 0012 Balance status 2byte R/UINT16
                                        # 0013-0014 - - - - Reserved 
        self.bVoltages = []
        for i in range(15, 30):         # 0015-0030 Cell voltage 32byte R/UINT16 mV, Voltage of 16 cells, 2 byte for each cell 
            if b[i] != 65535:
                self.bVoltages += [b[i]/1000]
        self.bTemperatures = []
        for i in range(31, 34):         # 0031-0034 Cell temperature 8byte R/INT16 0.1℃, 4 cell temperature, 2 byte for each cell 
            if b[i] != 65535:
                self.bTemperatures += [self.signedInt(b[i])/10]
        self.bMOSFETtemperature = self.signedInt(b[35])/10      # 0035 MOSFET temperature 2byte R/INT16 0.1℃ Or invalid 
        self.bEnvironmentTemperature = self.signedInt(b[36])/10 # 0036 Environment temperature 2byte R/INT16 0.1℃ Or invalid
        return b

    def readRegister(self, register: int, length: int, message: str):
        if hasattr(self, 'scc'): # check if we are live in production or unit testing
            r = super().readRegister(register, length)
            self.Log(logRead, f"{message}: {r}")
        else:
            if register in utMessages:
                r = utMessages[register]
            else:
                r = utRead(register)
        return r

# unit test section
def utRead(register: int): # ask for inverter response from console
    r = input(f"Enter message for {register}: ").encode('utf-8')
    return r

# Example usage
if __name__ == "__main__": # testing and debugging
    utMessages = {
        0: [63946, 2604, 40, 100, 8095, 20000, 20000, 66, 65535, 0, 0, 3584, 0, 65535, 65535, 3252, 3253, 3250, 3248, 3253, 3253, 3251, 3249, 65535, 65535, 65535, 65535, 65535, 65535, 65535, 65535, 156, 159, 65535, 65535, 160, 177]
        }

    b: bms = bmsMUST(3, "SIMULATOR")
    print(b.jSON())