from datetime import datetime
from zoneinfo import ZoneInfo
import platform
import time
import minimalmodbus
import serial

def addText(t1:str, t2: str, separator: str = ", "): # used to concatenate strings in warning and error messages to add comma separation where needed
    return t1 + separator + t2 if t1 != "" else t2

def dtKyiv(t:datetime):
    return t.astimezone(ZoneInfo('Europe/Kyiv')).strftime('%d@%H:%M')

class UPS(object): # base class for everything
    def __init__(self, logDetail: int):
        if platform.system() == "Linux": # read Raspberry CPU temperature
            try:
                with open('/sys/class/thermal/thermal_zone0/temp', 'r') as file:
                    self.rpiTemperature: float = round(float(file.read()) / 1000.0, 1)
            except:
                self.rpiTemperature: float = 0.0
        else:
            print(f"Platform is {platform.system()}")
            self.rpiTemperature: float = 0.0

        self.logDetail: int = logDetail

        self.ccBatteryFloatVoltage: float = 0.0

        self.icEnergyUse: str = ""
        self.icSolarUseAim: str = ""
        self.icBatteryStopDischarging: float = 0.0
        self.icBatteryStopCharging: float = 0.0
        self.icBatteryEqualization: float = 0.0
        self.icChargerSourcePriority: str = ""
        self.icMaxUtiChargeCurrent: int = 0

        self.pvWorkState: str = ""
        self.pvVoltage: float = 0.0
        self.pvBatteryVoltage: float = 0.0
        self.pvChargerCurrent: float = 0.0
        self.pvChargerPower: int = 0
        self.pvRadiatorTemperature: int = 0
        self.pvError: str = ""
        self.pvWarning: str = ""
        self.pvAccumulatedPower: float = 0.0
        self.pvReturnGrid: int = 0

        self.iWorkState: str =""
        self.iBatteryVoltage: float = 0.0
        self.iVoltage: float = 0.0
        self.iGridVoltage: float = 0.0
        self.iPInverter: int = 0
        self.iPGrid: int = 0
        self.iPLoad: int = 0
        self.iLoadPercent: int = 0
        self.iSInverter: int = 0
        self.iSGrid: int = 0
        self.iSLoad: int = 0
        self.iRadiatorTemperature: int = 0
        self.iAccumulatedLoadPower: float = 0.0
        self.iAccumulatedDischargerPower: float = 0.0
        self.iAccumulatedSelfusePower: float = 0.0
        self.iError:  str = ""
        self.iWarning: str = ""
        self.iBattPower: int = 0
        self.iBattCurrent: int = 0

        self.BestEnergyMsg: str = ""

    def addNotEmpty(self, f: dict, key: str, e:any): # add only not empty values to json in order to save memory and bandwith
        if hasattr(self, key):
            v = getattr(self, key)
            if v != e:
                f[key] = v

    def jSON(self, uKey: str) -> str:
        f = { # must have fields
            "pvVoltage": self.pvVoltage,
            "pvChargerCurrent": self.pvChargerCurrent, 
            "pvChargerPower": self.pvChargerPower,
            "iBatteryVoltage": self.iBatteryVoltage,
            "iGridVoltage": self.iGridVoltage,
            "iPGrid": self.iPGrid,
            "iPLoad": self.iPLoad,
            "iPInverter": self.iPInverter,
            "iBattPower": self.iBattPower,
            "iBattCurrent": self.iBattCurrent
        }
        optionalValues = [ # optional fields to save space and traffic
            ("icEnergyUse", ''),
            ("icSolarUseAim", ''),
            ("pvWorkState", ''),
            ("pvBatteryVoltage", 0.0),
            ("pvRadiatorTemperature", 0),
            ("pvAccumulatedPower", 0),
            ("pvError", ''),
            ("pvWarning", ''),
            ("iWorkState", ''),
            ("iVoltage", 0.0),
            ("iLoadPercent", 0),
            ("iSInverter", 0),
            ("iSGrid", 0),
            ("iSLoad",  0),
            ("iRadiatorTemperature", 0),
            ("iAccumulatedLoadPower", 0.0),
            ("iAccumulatedDischargerPower", 0.0),
            ("iAccumulatedSelfusePower", 0.0),
            ("iError", ''),
            ("iWarning", ''),
            ("rpiTemperature", 0),
            ("tRadiatorTemperature", 0),
            ("bRadiatorTemperature", 0),
            ("pvReturnGrid", 0),
            ("icChargerSourcePriority", ""),
            ("BestEnergyMsg", "")
        ]
        for key, value in optionalValues:
            self.addNotEmpty(f, key, value)

        return [
            {
                "measurement": "inverter",
                "tags": { "uKey": uKey },
                "fields": f
            }
        ]

    def Log(self, logLevel: int, message: str):
        if self.logDetail >= logLevel:
            print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\t{message}")

class UPSmgr(UPS): # base class for smarter solar power and battery management (use most of solar but still save battery)
    def setSBU(self):
        self.Log(1, "set SBU")
        return True

    def setSUB(self):
        self.Log(1, "set SUB")
        return True

    def setUtility(self):
        self.Log(1, "set UTI")
        return True

    def setCSO(self):
        self.Log(1, "set CSO")
        return True

    def setSNU(self):
        self.Log(1, "set SNU")
        return True

    def setOSO(self):
        self.Log(1, "set OSO")
        return True

    def moreSolar(self):
        self.Log(2, self.BestEnergyMsg)
        return self.setOSO()

    def saveBattery(self, intenseCharge: bool = False):
        self.Log(2, self.BestEnergyMsg)
        if intenseCharge:
            return self.setSNU()
        else:
            return self.setOSO()
        
    def setFloat(self, voltage: float):
        self.Log(1, f"set FLoat {voltage}V")
        return True

    def setGridChargingCurrent(self, current: int):
        self.Log(1, f"set Grid Charging {current}A")
        return True

    def setGridCharging(self, mode: str, curent: int):
        self.Log(1, f"set Grid Charging {mode} {curent}A")
        return True

    # todo: Solar Use Aim LBU - BLU depending on battery SOC and future estimate
    # todo: Charger source priority OSO - SNU - CSO depending on battery SOC and tomorrow estimate

    def setBestEnergySOC(self, TargetDetected: datetime, LowDetected: datetime, MinDetected: datetime):
        if TargetDetected is not None and (LowDetected is None or TargetDetected < LowDetected):
            self.Log(3, f"Target level shall be reached first at {dtKyiv(TargetDetected)}, Low at {LowDetected}")
            if self.icEnergyUse.upper() in {"UTI", "SUB"}:
                self.BestEnergyMsg = f"T {dtKyiv(TargetDetected)}"
                return 1 if self.moreSolar() else 0
        elif LowDetected is not None:
            self.Log(3, f"Low level could be reached first on {dtKyiv(LowDetected)}, Target on {TargetDetected}")
            if self.icEnergyUse.upper() in {"SBU", "SUB"}:
                self.BestEnergyMsg = f"L {dtKyiv(LowDetected)}"
                if self.pvChargerPower < self.iPLoad:
                    return -1 if self.saveBattery(MinDetected is not None) else 0
            if MinDetected is not None:
                self.BestEnergyMsg = addText(self.BestEnergyMsg, f"M {dtKyiv(MinDetected)})")
                self.Log(2, f"!!! Battery would be depleted below minimum on {dtKyiv(MinDetected)}")
        return None

    def setBestEnergyUse(self, solarVoltageOn: float, solarVoltageOff: float):
        if self.logDetail >= 3:
            print(f"Check Solar Voltage {solarVoltageOff} > {self.pvVoltage} > {solarVoltageOn}")
        match self.icEnergyUse.upper():
            case "UTI" | "SUB": # Utility or PV mixing mode
                if solarVoltageOn > 1 and self.iBatteryVoltage > self.icBatteryStopCharging:
                    if self.pvVoltage > solarVoltageOn and self.pvChargerPower > 0: # likely PV can produce more - however more sophisticated formula needed since voltage depends on power produced
                        self.BestEnergyMsg = f"Solar ON by Voltage {self.pvVoltage} > {solarVoltageOn} V"
                        return self.moreSolar()
                    # todo: mind solar use aim LBU - BLU here
                    elif self.icSolarUseAim == "LBU" and self.pvChargerPower > self.iPLoad and self.pvVoltage > solarVoltageOff: #+ self.iInternalUsePower: # PV produces enough just charging - technically charging can be delayed
                        self.BestEnergyMsg = f"Solar ON by Power {self.pvChargerPower} > {self.iPLoad} W"
                        return self.moreSolar()
                #elif : # more than equalization and pv > avg(on, off) meaning battery is overcharged
            case "SBU" | "SUB": # PV full production mode
                if solarVoltageOff > 1 and self.pvChargerPower < self.iPLoad: # solar power not enough
                    solarVoltageOff = solarVoltageOff * (1 - (self.pvChargerPower / 10000)) # mind possible 1% drop for every 100W production
                    if self.iBattCurrent > 0 and self.icBatteryStopCharging - self.icBatteryStopDischarging > 1: # mind 1V voltage drop under 50A high load for non-Li batteries
                        stopDischarge = self.icBatteryStopDischarging - (self.iBattCurrent / 50) 
                    else:
                        stopDischarge = self.icBatteryStopDischarging
                    if self.iPGrid >= self.iPLoad and self.iBatteryVoltage < (self.icBatteryStopCharging + stopDischarge) / 2: # working from Grid
                        self.BestEnergyMsg = f"Solar Off by Grid {self.iPGrid} >= Load {self.iPLoad} > PV {self.pvChargerPower} W & {self.iBatteryVoltage} < avg({self.icBatteryStopCharging} {stopDischarge:.2f}) V"
                        return self.saveBattery()  
                    elif self.iBattPower > self.pvChargerPower and self.iBatteryVoltage <= stopDischarge: # depleting battery too much
                        self.BestEnergyMsg = f"Solar Off by Batt {self.iBattPower} > PV {self.pvChargerPower} < Load {self.iPLoad} W & {self.iBatteryVoltage} <= {stopDischarge:.2f} V"
                        return self.saveBattery()                    
                    elif self.pvVoltage < solarVoltageOff: # better to be more sophisticated formula accounting MPPT since voltage depend on produced power
                        self.BestEnergyMsg = f"Solar Off by PV {self.pvVoltage} < {solarVoltageOff:.2f} V"
                        return self.saveBattery()
        return False

class UPSmodbus(UPS): # base class for modbus communication (USB)
    def __init__(self, logDetail: int, device_path: str, device_id: int, baud_rate: int):
        super().__init__(logDetail)

        if device_path != "SIMULATOR":
            self.scc = minimalmodbus.Instrument(device_path, device_id)
            self.scc.serial.baudrate = baud_rate
            self.scc.serial.timeout = 0.5
            self.scc.debug = logDetail >= 3

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

class UPSoffgrid(UPSmgr): # base class for off grid type invertors
    def moreSolar(self):
        #if self.pvChargerPower > self.iPLoad:
        #    if self.iBatteryVoltage > (self.icBatteryStopCharging + self.icBatteryStopDischarging) / 2:
        #        return super().moreSolar() and self.setSBU()
        #else:
            if self.iBatteryVoltage >= self.ccBatteryFloatVoltage:
                return super().moreSolar() and self.setSBU()
    def saveBattery(self):
        return super().saveBattery() and self.setUtility()

class UPSserial(UPS): # base class for serial communication (RS232)
    def __init__(self, logDetail: int, device_path: str, baud_rate: int):
        super().__init__(logDetail)

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

class UPShybrid(UPSmgr): # base class for hybrid type invertors
    def moreSolar(self):
        self.Log(1, f"More Solar {self.iBatteryVoltage} >= avg({self.icBatteryStopCharging} {self.icBatteryStopDischarging}) V")
        if self.iBatteryVoltage > (self.icBatteryStopCharging + self.icBatteryStopDischarging) / 2:
            return super().moreSolar() and self.setSBU()
        else:
            return super().moreSolar() and self.setSUB()
    def saveBattery(self):
        self.Log(1, f"Save Battery {self.iBatteryVoltage} <= avg({self.icBatteryStopCharging} {self.icBatteryStopDischarging}) V")
        if self.iBatteryVoltage < (self.icBatteryStopCharging + self.icBatteryStopDischarging) / 2:
            return super().saveBattery() and self.setUtility()
        else:
            return super().saveBattery() and self.setSUB()

# Example usage
if __name__ == "__main__":
    i = UPSmgr(True)
    i.icEnergyUse = "SBU"
    i.pvVoltage = 10
    i.pvChargerPower = 50
    i.iPLoad = 100
    i.iBattCurrent = 20
    i.icBatteryStopDischarging = 24
    i.icBatteryStopCharging = 29

    i.setBestEnergyUse(70,30)
    print(i.jSON("UPS"))
