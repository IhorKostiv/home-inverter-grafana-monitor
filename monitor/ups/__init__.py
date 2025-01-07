import platform
from time import strftime
from typing import Self
from unicodedata import east_asian_width
import minimalmodbus
import serial
from dataclasses import dataclass
from gpiozero import CPUTemperature
from gpiozero.pins.pigpio import PiGPIOFactory

class UPS(object):
    def __init__(self, isDebug: bool):
        if platform.system() == "Linux":
            try:
                factory = PiGPIOFactory()
                self.rpiTemperature = CPUTemperature(pin_factory=factory).temperature
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

    def jSON(self, uKey: str) -> str:
        return [
            {
                "measurement": "inverter",
                "tags": { "uKey": uKey },
                "fields": {
                    "icEnergyUse": self.icEnergyUse,
                    "fPVEstimate": self.fPVEstimate,
                    "pvWorkState": self.pvWorkState,
                    "pvVoltage": self.pvVoltage,
                    "pvBatteryVoltage": self.pvBatteryVoltage,
                    "pvChargerCurrent": self.pvChargerCurrent,
                    "pvChargerPower": self.pvChargerPower,
                    "pvRadiatorTemperature": self.pvRadiatorTemperature,
#                    "pvBatteryRelay": self.pvBatteryRelay,
#                    "pvRelay": self.pvRelay,
                    "pvAccumulatedPower": self.pvAccumulatedPower,
                    "pvError": self.pvError,
                    "pvWarning": self.pvWarning,
                    "iWorkState": self.iWorkState,
                    "iBatteryVoltage": self.iBatteryVoltage,
                    "iVoltage": self.iVoltage,
                    "iGridVoltage": self.iGridVoltage,
                    "iPInverter": self.iPInverter,
                    "iPGrid": self.iPGrid,
                    "iPLoad": self.iPLoad,
                    "iLoadPercent": self.iLoadPercent,
                    "iSInverter": self.iSInverter,
                    "iSGrid": self.iSGrid,
                    "iSLoad": self.iSLoad,
                    "iRadiatorTemperature": self.iRadiatorTemperature,
 #                   "iRelayState": self.iRelayState,
 #                   "iGridRelayState": self.iGridRelayState,
 #                   "iLoadRelayState": self.iLoadRelayState,
                    "iAccumulatedLoadPower": self.iAccumulatedLoadPower,
                    "iAccumulatedDischargerPower": self.iAccumulatedDischargerPower,
                    "iAccumulatedSelfusePower": self.iAccumulatedSelfusePower,
                    "iError": self.iError,
                    "iWarning": self.iWarning,
                    "iBattPower": self.iBattPower,
                    "iBattCurrent": self.iBattCurrent,
                    "rpiTemperature": self.rpiTemperature
                }
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