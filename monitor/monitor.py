
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

logDetail = int(os.environ.get("LOG_DETAIL", "0")) # 0 errors only, 1 +set commands, 2 +data, 3 +debug

USB_DEVICE = os.environ.get("USB_DEVICE", "SIMULATOR")
INVERTER_MODEL = os.environ.get("INVERTER_MODEL", "Axioma")
solarVoltageOn = float(os.environ.get("SOLAR_VOLTAGE_ON", "0"))
solarVoltageOff = float(os.environ.get("SOLAR_VOLTAGE_OFF", "0"))
PrecariousChargingEnabled = os.environ.get("PRECARIOUS_CHARGING_ENABLED", "False") == "True"
GridChargingEnabled = os.environ.get("GRID_CHARGING_ENABLED", "False") == "True"
GridChargingFloat = float(os.environ.get("GRID_CHARGING_FLOAT", "26.6"))
GridChargingBulk = float(os.environ.get("GRID_CHARGING_BULK", "27.8"))
GridChargingEstimate = os.environ.get("GRID_CHARGING_ESTIMATE", "")

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
    b: bms.bms = SUPPORTED_BMS[BMS_MODEL](logDetail, ACM_DEVICE)

    json_body = b.jSON(BMS_MODEL)
    if logDetail >= 3:
        print(datetime.now(), " ", json_body)
    client.write_points(json_body)

    bmsSOC = b.bSOC

if INVERTER_MODEL not in SUPPORTED_INVERTERS:
    print("Error: Unknown inverter model: {0}".format(INVERTER_MODEL))
    exit(1)

inverter: UPSmgr = SUPPORTED_INVERTERS[INVERTER_MODEL](logDetail, USB_DEVICE)

if Estimate != '':
    sc = Solcast(client, MaxPowerLimit, int((TargetPower + MaxPowerLimit) / 2) if inverter.icEnergyUse.upper() in {"UTI", "SUB"} else TargetPower, LowPower, MinPower, gridTied, logDetail)
    sc.Calculate(datetime.now(timezone.utc), Estimate, 80)
    be = inverter.setBestEnergySOC(sc.TargetDetected, sc.LowDetected, sc.MinDetected)
    #if logDetail >= 3:
    print(f"{datetime.now()} Best energy result {be}")
elif solarVoltageOn > 1 or solarVoltageOff > 1:
    inverter.setBestEnergyUse(solarVoltageOn, solarVoltageOff)

# todo: charge from grid if midnight (0..5am) and battery depleted
 
json_body = inverter.jSON(INVERTER_MODEL)
if logDetail >= 3:
    print(datetime.now(), " ", json_body)
if USB_DEVICE != "SIMULATOR":
    client.write_points(json_body)

if USB_DEVICE != "SIMULATOR":
    if ACM_DEVICE != "SIMULATOR" and INVERTER_MODEL == "Axioma": # workaround for Axioma inverter inability to properly manage battery charging voltage
        currentPower = b.bRemain  * 25.6
        if Estimate != '' and GridChargingEnabled and GridChargingEstimate != "":
            sc.Calculate(datetime.now(timezone.utc), GridChargingEstimate, 80)
            if sc.LowDetected is None or (sc.TargetDetected is not None and sc.TargetDetected < sc.LowDetected): # we can live on solar (optimistic or realistic)
                if inverter.icChargerSourcePriority.upper() != "OSO" or inverter.icMaxUtiChargeCurrent != 2:
                    inverter.setGridCharging("OSO", 2) # OSO, 2A
            else:
                '''if b.bBalance != '': overall no need to slow down, battery itself does it pretty good
                    maxUtiChargeCurent = 2
                elif currentPower > TargetPower:
                    maxUtiChargeCurent = 10
                else:'''
                maxUtiChargeCurent = 20
                print(f"B {b.bBalance} CP {currentPower:.1f} TP {TargetPower} UCC {maxUtiChargeCurent}")
                if sc.MinDetected is not None and sc.TargetDetected is None:
                    if inverter.icChargerSourcePriority.upper() != "SNU" or inverter.icMaxUtiChargeCurrent != maxUtiChargeCurent:
                        inverter.setGridCharging("SNU", maxUtiChargeCurent) # SNU, 20A
                else:
                    if inverter.icChargerSourcePriority.upper() != "CSO" or inverter.icMaxUtiChargeCurrent != maxUtiChargeCurent:
                        inverter.setGridCharging("CSO", maxUtiChargeCurent) # though would be good to calculate current based on electricity availability schedule
            tp = TargetPower if sc.MinDetected else TargetPower - MaxPowerLimit + TargetPower
        else:
            tp = TargetPower 
        if PrecariousChargingEnabled:
            notBalancing = True # overbalancing hurts b.bBalance == "" # todo: implement timeout for balancing
            if currentPower < tp and (inverter.pvChargerPower > 0 or inverter.icChargerSourcePriority.upper() != "OSO") and inverter.ccBatteryFloatVoltage < GridChargingBulk:
                if logDetail >= 3:
                    print(f"Charging start {currentPower:.1f}<{TargetPower}W {inverter.pvChargerPower:.1f}>0W {inverter.icChargerSourcePriority.upper()}")
                inverter.setFloat(GridChargingBulk) # 27.9 makes 100% sharply, 27.8 up to 91% charge
                # use SNU for 27.8 and then decrease current to 2 or 10A until reach target
            elif currentPower > TargetPower and b.bCurrent <= 0 and notBalancing and inverter.ccBatteryFloatVoltage > GridChargingFloat: #bms current is reverse; wait until balanced
                if logDetail >= 3:
                    print(f"Charging complete {currentPower:.1f}>{TargetPower}W {b.bCurrent:.1f}A")
                inverter.setFloat(GridChargingFloat)
            elif currentPower >= MaxPowerLimit and notBalancing and inverter.ccBatteryFloatVoltage > GridChargingFloat:
                if logDetail >= 3:
                    print(f"Charging limit {currentPower:.1f}>={MaxPowerLimit}W")
                inverter.setFloat(GridChargingFloat)
            elif inverter.pvChargerPower <= 0 and inverter.icChargerSourcePriority.upper() == "OSO" and inverter.ccBatteryFloatVoltage > GridChargingFloat:
                if logDetail >= 3:
                    print(f"Charging stop {inverter.pvChargerPower:.1f}<=0W {inverter.icChargerSourcePriority.upper()}")
                inverter.setFloat(GridChargingFloat)

    elif INVERTER_MODEL == "GreenCell" and GridChargingEnabled: # workaround for GreenCell inverter inability to properly charge battery from grid
        if inverter.iBatteryVoltage < GridChargingFloat and inverter.iBattPower <= 0 and inverter.pvVoltage < 14 and inverter.icChargerSourcePriority.upper() == "OSO":
            inverter.setCSO() # todo: not to trigger it on discharging - measue when battery is calm
        elif PrecariousChargingEnabled and inverter.iBatteryVoltage < 13.3 and inverter.pvVoltage < 14 and inverter.icChargerSourcePriority.upper() != "OSO":
            inverter.setFloat(GridChargingBulk) # better set SNU/CSO
        elif inverter.iBatteryVoltage >= GridChargingBulk and inverter.iRadiatorTemperature < inverter.rpiTemperature:
            if PrecariousChargingEnabled and inverter.ccBatteryFloatVoltage > GridChargingFloat:
                inverter.setFloat(GridChargingFloat)
            inverter.setOSO()
        elif PrecariousChargingEnabled and inverter.pvVoltage >= 14 and inverter.icChargerSourcePriority.upper() != "SNU":
            inverter.setFloat(GridChargingFloat)
        elif PrecariousChargingEnabled and inverter.iGridVoltage < 100 and inverter.ccBatteryFloatVoltage > GridChargingFloat:
            inverter.setFloat(GridChargingFloat)