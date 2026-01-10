
from influxdb import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS, ASYNCHRONOUS

import os
from datetime import datetime, timezone
from ups import UPSmgr, greenCell, axioma #, must_ep3000, must_pv1800, must_ph18_5248
import json
from ups import bms
from solcast import Solcast

SUPPORTED_INVERTERS = {
    "GreenCell": greenCell.GreenCell,
    "Axioma": axioma.Axioma
#    "must-pv1800": must_pv1800.MustPV1800,
#    "must-ep3000": must_ep3000.MustEP3000,
#    "must-ph18-5248": must_ph18_5248.MustPH185248
}

SUPPORTED_BMS = {
    "MUST": bms.MUST
    }

DB_HOST = os.environ.get("DB_HOST", "inverter")
DB_PORT = int(os.environ.get("DB_PORT", "8086"))
DB_USERNAME = os.environ.get("DB_USERNAME", "root")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "root")
DB_NAME = os.environ.get("DB_NAME", "ups")

isDebug = os.environ.get("IS_DEBUG", "True") == "False"

USB_DEVICE = os.environ.get("USB_DEVICE", "SIMULATOR")
INVERTER_MODEL = os.environ.get("INVERTER_MODEL", "Axioma")
solarVoltageOn = float(os.environ.get("SOLAR_VOLTAGE_ON", "0"))
solarVoltageOff = float(os.environ.get("SOLAR_VOLTAGE_OFF", "0"))
#gridCharging = os.environ.get("GRID_CHARGING", "26.0,")

ACM_DEVICE = os.environ.get("ACM_DEVICE", "SIMULATOR")
BMS_MODEL = os.environ.get("BMS_MODEL", "MUST")

gridTied = os.environ.get("GRID_TIED", "").split(",")
Estimate = os.environ.get("SOLCAST_ESTIMATE", '')
MaxPowerLimit = int(os.environ.get("MAX_POWER_LIMIT", "5120"))  # full battery capacity
TargetPower = int(os.environ.get("TARGET_POWER", "4900"))       # 95% approx
LowPower = int(os.environ.get("LOW_POWER", "1500"))             # 30% approx
MinPower = int(os.environ.get("MIN_POWER", "1024"))             # 20% approx

if USB_DEVICE != "SIMULATOR" or ACM_DEVICE != "SIMULATOR":
    client = InfluxDBClient(DB_HOST, DB_PORT, DB_USERNAME, DB_PASSWORD, DB_NAME)

bmsSOC = -1
if ACM_DEVICE != "SIMULATOR":
    b: bms.bms = SUPPORTED_BMS[BMS_MODEL](isDebug, ACM_DEVICE)

    json_body = b.jSON(BMS_MODEL)
    if isDebug:
        print(datetime.now(), " ", json_body)
    client.write_points(json_body)

    bmsSOC = b.bSOC

if INVERTER_MODEL not in SUPPORTED_INVERTERS:
    print("Error: Unknown inverter model: {0}".format(INVERTER_MODEL))
    exit(1)

inverter: UPSmgr = SUPPORTED_INVERTERS[INVERTER_MODEL](isDebug, USB_DEVICE)

if Estimate != '':
    sc = Solcast(client, MaxPowerLimit, int((TargetPower + MaxPowerLimit) / 2) if inverter.icEnergyUse.upper() in {"UTI", "SUB"} else TargetPower, LowPower, MinPower, isDebug)
    sc.Calculate(datetime.now(timezone.utc), Estimate, 80, gridTied)
    inverter.setBestEnergySOC(sc.TargetDetected, sc.LowDetected, sc.MinDetected)
elif solarVoltageOn > 1 or solarVoltageOff > 1:
    inverter.setBestEnergyUse(solarVoltageOn, solarVoltageOff)

# todo: charge from grid if midnight (0..5am) and battery depleted
 
json_body = inverter.jSON(INVERTER_MODEL)
if isDebug:
    print(datetime.now(), " ", json_body)
if USB_DEVICE != "SIMULATOR":
    client.write_points(json_body)