
from influxdb import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS, ASYNCHRONOUS

import os
from datetime import datetime
from tzlocal import get_localzone
from ups import UPS, greenCell, axioma #, must_ep3000, must_pv1800, must_ph18_5248
from forecastsolar import pvEstimate
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
solarVoltageOn = float(os.environ.get("SOLAR_VOLTAGE_ON", "0.96"))
solarVoltageOff = float(os.environ.get("SOLAR_VOLTAGE_OFF", "0.82"))

client = InfluxDBClient(DB_HOST, DB_PORT, DB_USERNAME, DB_PASSWORD, DB_NAME)

if INVERTER_MODEL not in SUPPORTED_INVERTERS:
    print("Error: Unknown inverter model: {0}".format(INVERTER_MODEL))
    exit(1)

inverter: UPS = SUPPORTED_INVERTERS[INVERTER_MODEL](isDebug, USB_DEVICE)

forecast = client.query("SELECT last(""Response"") as Response, last(""TimeZone"") as TimeZone FROM ""forecast"" ORDER BY time DESC")
if isDebug:
    print("Forecast: ", forecast)
fl = list(forecast.get_points("forecast"))
if len(fl) > 0:
    js = json.loads(str(fl[0]).replace("'", '"').replace('"{',"{").replace('}"',"}"))
    if isDebug:
        print(js)
    inverter.setFPVEstimate(pvEstimate(datetime.now(get_localzone()), js))

json_body = inverter.jSON(INVERTER_MODEL)
if isDebug:
    print(datetime.now(), " ", json_body)

if USB_DEVICE != "SIMULATOR":
    client.write_points(json_body)

if solarVoltageOn > 0 and solarVoltageOff > 0 and (solarVoltageOn < 1 or solarVoltageOff < 1):
    sv = client.query("SELECT max(""pvVoltage"") as pvVoltage FROM ""inverter"" WHERE time >= now() - 7d")
    if (len(sv)) > 0:
        for t in sv:
            pv = float(t[0]['pvVoltage'])
            if solarVoltageOn > 0 and solarVoltageOn < 1:
                solarVoltageOn = solarVoltageOn * pv
            if solarVoltageOff > 0 and solarVoltageOff < 1:
                solarVoltageOff = solarVoltageOff * pv
            if isDebug:
                print(f"Solar Voltage ON {solarVoltageOn} OFF {solarVoltageOff}")
            break
    else:
        solarVoltageOn = solarVoltageOff = 0
        if isDebug:
            print("Solar Voltage Zero")

inverter.setBestEnergyUse(solarVoltageOn, solarVoltageOff)