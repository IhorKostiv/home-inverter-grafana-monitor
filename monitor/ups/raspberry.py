from gpiozero import pi_info
import platform
import subprocess
if __name__ == '__main__':
    from __init__ import device 
    from _constants_ import *
else:
    from ups import device
    from ups._constants_ import *

class Raspberry(device):
    def __init__(self, logDetail):
        super().__init__(logDetail)
        self.measurement = "raspberry"
        self.uKey = self.readHWInfo()
        self.rpiThrottledNow = ''
        self.rpiThrottledPast = ''
        self.rpiTemperature = self.readTemperature()
        self.readThrottled()

    def _getMandatoryFields_(self):
        return {"rpiTemperature": self.rpiTemperature}
    def _getOptionalFields_(self):
        return [("rpiThrottledNow", ''), ("rpiThrottledPast", '')]
    
    def readHWInfo(self):
        if platform.system() == "Linux":
            return pi_info().model if pi_info().model is not None else "Unknown"
        else:
            return platform.system()
        
    def readTemperature(self):
        if platform.system() == "Linux": # read Raspberry CPU temperature
            try:
                with open('/sys/class/thermal/thermal_zone0/temp', 'r') as file:
                    return round(float(file.read()) / 1000.0, 1)
            except:
                return 0.0
        else:
            self.Log(logDebug, f"Platform is {platform.system()}")
            return 0.0
    
    def readThrottled(self):
        flags = { # Bitmask definitions for throttled flags
            0x00001: "Under-voltage",
            0x00002: "ARM frequency capped",
            0x00004: "Throttled",
            0x00008: "Soft temperature limit active",
            0x10000: "Under-voltage has occurred",
            0x20000: "ARM frequency capping has occurred",
            0x40000: "Throttling has occurred",
            0x80000: "Soft temperature limit has occurred"
            }
        if platform.system() == "Linux": # read Raspberry throttled status
            result = subprocess.run(["vcgencmd", "get_throttled"], capture_output=True, text=True)
            output = result.stdout.strip()
            if output.startswith("throttled="):
                hex_value = output.split("=")[1]
                self.rpiThrottledNow = self.bitmaskText(False,hex_value & 0xFFFF, flags) # current status from lower 16 bits
                self.rpiThrottledPast = self.bitmaskText(False, hex_value & 0xFFFF0000, flags) # historical status from upper 16 bits
        else:
            self.Log(logDebug, f"Platform is {platform.system()}")

if __name__ == '__main__':
    r = Raspberry(logDebug)
    json_body = r.jSON()
    r.Log(logDebug, json_body)
