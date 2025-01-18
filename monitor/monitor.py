
from influxdb import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS, ASYNCHRONOUS

import os
from datetime import datetime
from ups import UPSmgr, greenCell, axioma #, must_ep3000, must_pv1800, must_ph18_5248
import json

SUPPORTED_INVERTERS = {
    "GreenCell": greenCell.GreenCell,
    "Axioma": axioma.Axioma
#    "must-pv1800": must_pv1800.MustPV1800,
#    "must-ep3000": must_ep3000.MustEP3000,
#    "must-ph18-5248": must_ph18_5248.MustPH185248
}

USB_DEVICE = os.environ.get("USB_DEVICE", "SIMULATOR")

DB_HOST = os.environ.get("DB_HOST", "inverter")
DB_PORT = int(os.environ.get("DB_PORT", "8086"))
DB_USERNAME = os.environ.get("DB_USERNAME", "root")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "root")
DB_NAME = os.environ.get("DB_NAME", "ups")
INVERTER_MODEL = os.environ.get("INVERTER_MODEL", "Axioma")
isDebug = os.environ.get("IS_DEBUG", "True") == "True"
solarVoltageOn = float(os.environ.get("SOLAR_VOLTAGE_ON", "0"))
solarVoltageOff = float(os.environ.get("SOLAR_VOLTAGE_OFF", "0"))

if USB_DEVICE != "SIMULATOR":
    client = InfluxDBClient(DB_HOST, DB_PORT, DB_USERNAME, DB_PASSWORD, DB_NAME)

if INVERTER_MODEL not in SUPPORTED_INVERTERS:
    print("Error: Unknown inverter model: {0}".format(INVERTER_MODEL))
    exit(1)

inverter: UPSmgr = SUPPORTED_INVERTERS[INVERTER_MODEL](isDebug, USB_DEVICE)

json_body = inverter.jSON(INVERTER_MODEL)
if isDebug:
    print(datetime.now(), " ", json_body)

if USB_DEVICE != "SIMULATOR":
    client.write_points(json_body)

if solarVoltageOn > 1 and solarVoltageOff > 1:
    inverter.setBestEnergyUse(solarVoltageOn, solarVoltageOff)