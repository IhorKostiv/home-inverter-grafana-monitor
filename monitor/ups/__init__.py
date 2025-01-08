import platform
from time import strftime
from typing import Self
from unicodedata import east_asian_width
import minimalmodbus
import serial
from dataclasses import dataclass
from gpiozero import CPUTemperature

class UPS(object):
    def __init__(self, isDebug: bool):
        if platform.system() == "Linux":
            try:
                self.rpiTemperature = CPUTemperature().temperature
            except:
                pass
        else:
            print(f"Platform is {platform.system()}")

        self.isDebug: bool = isDebug
        self.icEnergyUse: str = ""
        self.icBatteryStopDischarging: float = 0.0
        self.icBatteryStopCharging: float = 0.0
        self.icBatteryEqualization: float = 0.0

        self.fPVEstimate: int = 0

        self.pvWorkState: str = ""
        self.pvVoltage: float = 0.0
        self.pvBatteryVoltage: float = 0.0
        self.pvChargerCurrent: float = 0.0
        self.pvChargerPower: int = 0
        self.pvRadiatorTemperature: int = 0
#        self.pvBatteryRelay: str = ""
#        self.pvRelay: str = ""
        self.pvError: str = ""
        self.pvWarning: str = ""
        self.pvAccumulatedPower: float = 0.0

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
 #       self.iRelayState: str = ""
 #       self.iGridRelayState: str = ""
 #       self.iLoadRelayState: str = ""
        self.iAccumulatedLoadPower: float = 0.0
        self.iAccumulatedDischargerPower: float = 0.0
        self.iAccumulatedSelfusePower: float = 0.0
        self.iError:  str = ""
        self.iWarning: str = ""
        self.iBattPower: int = 0
        self.iBattCurrent: int = 0
        self.rpiTemperature: float = 0.0

    def addNotEmpty(self, f: dict, key: str, value:any, e:any):
        if value != e:
            f[key] = value

    def jSON(self, uKey: str) -> str:
        f = {}
        self.addNotEmpty(f, "icEnergyUse", self.icEnergyUse, '')
        self.addNotEmpty(f, "fPVEstimate", self.fPVEstimate, 0)
        self.addNotEmpty(f, "pvWorkState", self.pvWorkState, '')
        self.addNotEmpty(f, "pvVoltage", self.pvVoltage, 0.0)
        self.addNotEmpty(f, "pvBatteryVoltage", self.pvBatteryVoltage, 0.0)
        self.addNotEmpty(f, "pvChargerCurrent", self.pvChargerCurrent, 0.0)
        self.addNotEmpty(f, "pvChargerPower", self.pvChargerPower, 0)
        self.addNotEmpty(f, "pvRadiatorTemperature", self.pvRadiatorTemperature, 0)
        self.addNotEmpty(f, "pvAccumulatedPower", self.pvAccumulatedPower, 0)
        self.addNotEmpty(f, "pvError", self.pvError, '')
        self.addNotEmpty(f, "pvWarning", self.pvWarning, '')
        self.addNotEmpty(f, "iWorkState", self.iWorkState, '')
        self.addNotEmpty(f, "iBatteryVoltage", self.iBatteryVoltage, 0.0)
        self.addNotEmpty(f, "iVoltage", self.iVoltage, 0.0)
        self.addNotEmpty(f, "iGridVoltage", self.iGridVoltage, 0.0)
        self.addNotEmpty(f, "iPInverter", self.iPInverter, 0)
        self.addNotEmpty(f, "iPGrid", self.iPGrid, 0)
        self.addNotEmpty(f, "iPLoad", self.iPLoad, 0)
        self.addNotEmpty(f, "iLoadPercent", self.iLoadPercent, 0)
        self.addNotEmpty(f, "iSInverter", self.iSInverter, 0)
        self.addNotEmpty(f, "iSGrid", self.iSGrid, 0)
        self.addNotEmpty(f, "iSLoad", self.iSLoad, 0)
        self.addNotEmpty(f, "iRadiatorTemperature", self.iRadiatorTemperature, 0)
        self.addNotEmpty(f, "iAccumulatedLoadPower", self.iAccumulatedLoadPower, 0.0)
        self.addNotEmpty(f, "iAccumulatedDischargerPower", self.iAccumulatedDischargerPower, 0.0)
        self.addNotEmpty(f, "iAccumulatedSelfusePower", self.iAccumulatedSelfusePower, 0.0)
        self.addNotEmpty(f, "iError", self.iError, '')
        self.addNotEmpty(f, "iWarning", self.iWarning, '')
        self.addNotEmpty(f, "iBattPower", self.iBattPower, 0)
        self.addNotEmpty(f, "iBattCurrent", self.iBattCurrent, 0)
        self.addNotEmpty(f, "rpiTemperature", self.rpiTemperature, 0.0)

        return [
            {
                "measurement": "inverter",
                "tags": { "uKey": uKey },
                "fields": f
    }
]

    def setSBU(self):
        if self.isDebug:
            print("set SBU")
        pass

    def setSUB(self):
        if self.isDebug:
            print("set SUB")
        pass

    def setUtility(self):
        if self.isDebug:
            print("set UTI")
        pass

    def setFPVEstimate(self, estimate: int):
        self.fpvEstimate = estimate

    def setBestEnergyUse(self, solarVoltageOn: float, solarVoltageOff: float):
        pass

class UPSmodbus(UPS):
    def __init__(self, isDebug: bool, device_path: str, device_id: int, baud_rate: int):
        super().__init__(isDebug)

        self.device_path = device_path
        self.device_id = device_id
        self.baud_rate = baud_rate

        self.scc = minimalmodbus.Instrument(device_path, device_id)
        self.scc.serial.baudrate = baud_rate
        self.scc.serial.timeout = 0.5
        self.scc.debug = isDebug

    def setBestEnergyUse(self, solarVoltageOn: float, solarVoltageOff: float):
        if self.iPInverter == 0:
            if self.icEnergyUse == "UTI":
                if self.fPVEstimate >= 0 and self.fPVEstimate > self.iPLoad:
                    print("Set Solar ON by Estimate")
                    self.setSBU()
                elif solarVoltageOn > 0 and self.pvVoltage > solarVoltageOn:
                    print("Set Solar ON by Voltage")
                    self.setSBU()
                #elif : # more than equalization and pv > avg(on, off)
            elif self.icEnergyUse == "SBU" and self.iBatteryVoltage < (self.icBatteryStopCharging + self.icBatteryStopDischarging) / 2:
                if self.fPVEstimate >= 0:
                    if self.fPVEstimate < self.iPLoad:
                        if solarVoltageOff > 0:
                           if self.pvVoltage < solarVoltageOff:
                                print("Set Solar Off by Estimate and Voltage")
                                self.setUtility()
                        else:
                            print("Set Solar Off by Estimate")
                            self.setUtility()
                else: # no estimate, operate only by Voltage
                    # actually below better to be more sophisticated formula accounting MPPT since voltage depend on produced power
                    if solarVoltageOff > 0 and self.pvVoltage < solarVoltageOff:
                        print("Set Solar Off by Voltage")
                        self.setUtility()

        pass

class UPSserial(UPS):
    def __init__(self, isDebug: bool, device_path: str, baud_rate: int):
        super().__init__(isDebug)

        if device_path != "SIMULATOR":
            self.scc = serial.Serial(device_path, baud_rate, timeout=1)

    def __del__(self):
        if hasattr(super, 'scc'):
            self.scc.close()