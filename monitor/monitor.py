
from influxdb import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS, ASYNCHRONOUS

import os
from datetime import datetime
from tzlocal import get_localzone
from ups import UPS, greenCell #, must_ep3000, must_pv1800, must_ph18_5248
from forecastsolar import pvEstimate
import json

#SUPPORTED_INVERTERS = {
#    "must-pv1800": must_pv1800.MustPV1800,
#    "must-ep3000": must_ep3000.MustEP3000,
#    "must-ph18-5248": must_ph18_5248.MustPH185248
#}

USB_DEVICE = os.environ.get("USB_DEVICE", "/dev/ttyUSB0")

DB_HOST = os.environ.get("DB_HOST", "inverter")
DB_PORT = int(os.environ.get("DB_PORT", "8086"))
DB_USERNAME = os.environ.get("DB_USERNAME", "root")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "root")
DB_NAME = os.environ.get("DB_NAME", "ups")
INVERTER_MODEL = os.environ.get("INVERTER_MODEL", "GreenCell")
isDebug = os.environ.get("IS_DEBUG", "True") == "True"

client = InfluxDBClient(DB_HOST, DB_PORT, DB_USERNAME, DB_PASSWORD, DB_NAME)

#if INVERTER_MODEL not in SUPPORTED_INVERTERS:
#    print("Unknown inverter model model: {0}".format(INVERTER_MODEL))
#    exit(1)

inverter: UPS = greenCell.GreenCell(USB_DEVICE) # SUPPORTED_INVERTERS[INVERTER_MODEL](USB_DEVICE)
sample = inverter.sample(isDebug)

forecast = client.query("SELECT last(""Response"") as Response, last(""TimeZone"") as TimeZone FROM ""forecast"" ORDER BY time DESC")
if isDebug:
    print("Forecast: ", forecast)
fl = list(forecast.get_points("forecast"))
if len(fl) > 0:
    js = json.loads(str(fl[0]).replace("'", '"').replace('"{',"{").replace('}"',"}"))
    if isDebug:
        print(js)
    sample.fPVEstimate = pvEstimate(datetime.now(get_localzone()), js)

if isDebug:
    print("Measured: {0}".format(sample))

json_body = sample.jSON(INVERTER_MODEL)

print(datetime.now(), " ", json_body)

client.write_points(json_body)
