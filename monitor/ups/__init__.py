from time import strftime
import minimalmodbus
from dataclasses import dataclass


@dataclass
class Sample(object):
    pvWorkState: str
    pvMpptState: str
    pvChargingState: str
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
 #   iBatterySOC: int


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
