
from influxdb import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS, ASYNCHRONOUS

import os
from ups import UPS, greenCell # must_ep3000, must_pv1800, must_ph18_5248


#SUPPORTED_INVERTERS = {
#    "must-pv1800": must_pv1800.MustPV1800,
#    "must-ep3000": must_ep3000.MustEP3000,
#    "must-ph18-5248": must_ph18_5248.MustPH185248
#}

USB_DEVICE = os.environ.get("USB_DEVICE", "/dev/ttyUSB0")

DB_HOST = os.environ.get("DB_HOST", "influxdb")
DB_PORT = int(os.environ.get("DB_PORT", "8086"))
DB_USERNAME = os.environ.get("DB_USERNAME", "root")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "root")
DB_NAME = os.environ.get("DB_NAME", "ups")
INVERTER_MODEL = os.environ.get("INVERTER_MODEL", "GreenCell")

client = InfluxDBClient(DB_HOST, DB_PORT, DB_USERNAME, DB_PASSWORD, DB_NAME)

#if INVERTER_MODEL not in SUPPORTED_INVERTERS:
#    print("Unknown inverter model model: {0}".format(INVERTER_MODEL))
#    exit(1)

inverter: UPS = greenCell.GreenCell(USB_DEVICE) # SUPPORTED_INVERTERS[INVERTER_MODEL](USB_DEVICE)
sample = inverter.sample()

print("Measured: {0}".format(sample))

json_body = [
    {
        "measurement": "inverter",
        "tags": {
            "model": INVERTER_MODEL,
            "pvWorkState": sample.pvWorkState,
            "pvMpptState": sample.pvMpptState,
            "pvChargingState": sample.pvChargingState,
            "pvBatteryRelay": sample.pvBatteryRelay,
            "pvRelay": sample.pvRelay,
            "pvError": sample.pvError,
            "pvWarning": sample.pvWarning,
            "iWorkState": sample.iWorkState,
            "iRelayState": sample.iRelayState,
            "iGridRelayState": sample.iGridRelayState,
            "iLoadRelayState": sample.iLoadRelayState,
            "iError": sample.iError,
            "iWarning": sample.iWarning
        },
        "fields": {
            "pvVoltage": sample.pvVoltage,
            "pvBatteryVoltage": sample.pvBatteryVoltage,
            "pvChargerCurrent": sample.pvChargerCurrent,
            "pvChargerPower": sample.pvChargerPower,
            "pvRadiatorTemperature": sample.pvRadiatorTemperature,
            "pvAccumulatedPower": sample.pvAccumulatedPower,
            "iBatteryVoltage": sample.iBatteryVoltage,
            "iVoltage": sample.iVoltage,
            "iGridVoltage": sample.iGridVoltage,
            "iPInverter": sample.iPInverter,
            "iPGrid": sample.iPGrid,
            "iPLoad": sample.iPLoad,
            "iLoadPercent": sample.iLoadPercent,
            "iSInverter": sample.iSInverter,
            "iSGrid": sample.iSGrid,
            "iSLoad": sample.iSLoad,
            "iRadiatorTemperature": sample.iRadiatorTemperature,
            "iAccumulatedLoadPower": sample.iAccumulatedLoadPower,
            "iAccumulatedDischargerPower": sample.iAccumulatedDischargerPower,
            "iAccumulatedSelfusePower": sample.iAccumulatedSelfusePower,
            "iBattPower": sample.iBattPower,
            "iBattCurrent": sample.iBattCurrent
        }
    }
]

print(json_body)

client.write_points(json_body)
