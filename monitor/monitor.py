
from influxdb import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS, ASYNCHRONOUS

import os
from datetime import datetime
from tzlocal import get_localzone
from ups import Sample, UPS, greenCell #, must_ep3000, must_pv1800, must_ph18_5248
from forecastsolar import pvEstimate
import json

#SUPPORTED_INVERTERS = {
#    "must-pv1800": must_pv1800.MustPV1800,
#    "must-ep3000": must_ep3000.MustEP3000,
#    "must-ph18-5248": must_ph18_5248.MustPH185248
#}

USB_DEVICE = os.environ.get("USB_DEVICE", "SIMULATOR")

DB_HOST = os.environ.get("DB_HOST", "inverter")
DB_PORT = int(os.environ.get("DB_PORT", "8086"))
DB_USERNAME = os.environ.get("DB_USERNAME", "root")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "root")
DB_NAME = os.environ.get("DB_NAME", "ups")
INVERTER_MODEL = os.environ.get("INVERTER_MODEL", "GreenCell")
isDebug = os.environ.get("IS_DEBUG", "True") == "True"
solarVoltageOn = float(os.environ.get("SOLAR_VOLTAGE_ON", "0.96"))
solarVoltageOff = float(os.environ.get("SOLAR_VOLTAGE_OFF", "0.82"))

client = InfluxDBClient(DB_HOST, DB_PORT, DB_USERNAME, DB_PASSWORD, DB_NAME)

#if INVERTER_MODEL not in SUPPORTED_INVERTERS:
#    print("Unknown inverter model model: {0}".format(INVERTER_MODEL))
#    exit(1)

if USB_DEVICE != "SIMULATOR":
    inverter: UPS = greenCell.GreenCell(USB_DEVICE) # SUPPORTED_INVERTERS[INVERTER_MODEL](USB_DEVICE)
    sample = inverter.sample(isDebug)
else:
    print("Simulation")
    sample = Sample( "SBU", 25, 26, 220,
        "Sample", 37, 24, 3, 72, 25, "On", "On", "pvError", "pvWarning", 102,
        "Sample", 24, 220, 220, 0, 220, 150, 5, 0, 220, 150, 26, "On", "On", "On", 1024, 123, 123, "iError", "iWarning", -24, -1,
        27 )

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
        print("Solar Voltage Zero")

if sample.iPInverter == 0:
    if sample.icEnergyUse == "UTI":
        if sample.fPVEstimate >= 0 and sample.fPVEstimate > sample.iPLoad:
            print("Set Solar ON by Estimate")
            inverter.setSolar(isDebug)
        elif solarVoltageOn > 0 and sample.pvVoltage > solarVoltageOn:
            print("Set Solar ON by Voltage")
            inverter.setSolar(isDebug)
        #elif : # more than equalization and pv > avg(on, off)
    elif sample.icEnergyUse == "SBU" and sample.iBatteryVoltage < (sample.icBatteryStopCharging + sample.icBatteryStopDischarging) / 2:
        if sample.fPVEstimate >= 0:
            if sample.fPVEstimate < sample.iPLoad:
                if solarVoltageOff > 0:
                   if sample.pvVoltage < solarVoltageOff:
                        print("Set Solar Off by Estimate and Voltage")
                        inverter.setUtility(isDebug)
                else:
                    print("Set Solar Off by Estimate")
                    inverter.setUtility(isDebug)
        else: # no estimate, operate only by Voltage
            # actually below better to be more sophisticated formula accounting MPPT since voltage depend on produced power
            if solarVoltageOff > 0 and sample.pvVoltage < solarVoltageOff:
                print("Set Solar Off by Voltage")
                inverter.setUtility(isDebug)
            