from time import strftime
from typing import Self
import minimalmodbus
from dataclasses import dataclass


@dataclass
class Sample(object):
    icEnergyUse: str
    fPVEstimate: int

    pvWorkState: str
    pvVoltage: float
    pvBatteryVoltage: float
    pvChargerCurrent: float
    pvChargerPower: int
    pvRadiatorTemperature: int
    pvBatteryRelay: str
    pvRelay: str
    pvError: str
    pvWarning: str
    pvAccumulatedPower: float

    iWorkState: str
    iBatteryVoltage: float
    iVoltage: float
    iGridVoltage: float
    iPInverter: int
    iPGrid: int
    iPLoad: int
    iLoadPercent: int
    iSInverter: int
    iSGrid: int
    iSLoad: int 
    iRadiatorTemperature: int
    iRelayState: str
    iGridRelayState: str
    iLoadRelayState: str
    iAccumulatedLoadPower: float
    iAccumulatedDischargerPower: float
    iAccumulatedSelfusePower: float
    iError:  str
    iWarning: str
    iBattPower: int
    iBattCurrent: int
    rpiTemperature: float

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
                    "pvBatteryRelay": self.pvBatteryRelay,
                    "pvRelay": self.pvRelay,
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
                    "iRelayState": self.iRelayState,
                    "iGridRelayState": self.iGridRelayState,
                    "iLoadRelayState": self.iLoadRelayState,
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


class UPS(object):
    def __init__(self, device_path: str, device_id: int, baud_rate: int):
        self.device_path = device_path
        self.device_id = device_id
        self.baud_rate = baud_rate

        self.scc = minimalmodbus.Instrument(device_path, device_id)
        self.scc.serial.baudrate = baud_rate
        self.scc.serial.timeout = 0.5

    def sample(self) -> Sample:
        pass

    def setSolar(self, isDebug: bool):
        pass

    def setUtility(self, isDebug: bool):
        pass