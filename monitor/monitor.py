from datetime import datetime, timezone
import platform
import sys
import time
from ups._bms_ import bms
from ups._constants_ import *
from ups._data_ import DataStore
from ups._inverter_ import inverterMgr
from ups import greenCell, axioma #, must_ep3000, must_pv1800, must_ph18_5248
from ups import bmsMust
from solcast import Solcast

SUPPORTED_INVERTERS = {
    "GreenCell": greenCell.GreenCell,
    "Axioma": axioma.Axioma
#    "must-pv1800": must_pv1800.MustPV1800,
#    "must-ep3000": must_ep3000.MustEP3000,
#    "must-ph18-5248": must_ph18_5248.MustPH185248
}

SUPPORTED_BMS = {
    "MUST": bmsMust.bmsMUST
    }
# Usage: python3 monitor.py <DB_HOST> <DB_PORT> <DB_USERNAME> <DB_PASSWORD> <DB_NAME>
# Example: python3 monitor.py inverter.local 8086 root root ups
ds = DataStore() # initialize datastore to read settings and connect to database
if len(sys.argv) >= 6: # from command line always show debug info, and wait till mid-minute to not interfere with possible scdeduled task
    ds.LogDetail = 3
    s = 30 - datetime.now().second
    if s > 0 or s < -15: # possible execution window is 30..45th sec of minute
        if s < 0:
            s += 60
        print(f"Wait {s}s...")
        time.sleep(s)

if ds.bmsModel in SUPPORTED_BMS: # initialize BMS if configured, read data and write to database
    b: bms = SUPPORTED_BMS[ds.bmsModel](ds.LogDetail, ds.bmsNode)
    json_body = b.jSON()
    b.Log(logDebug, json_body)
    ds.write(json_body)
    currentPower = b.CurrentPower
elif ds.bmsModel != "": # if BMS model is not empty but unsupported, print error and exit
    ds.Log(logError, f"Unknown BMS model: {ds.bmsModel}")
    exit(1)
else: # no BMS configured, set SOC to -1 to indicate unknown state
    currentPower = -1

if ds.InverterModel not in SUPPORTED_INVERTERS:
    ds.Log(logError, f"Unknown inverter model: {ds.InverterModel}")
    exit(1)

inverter: inverterMgr = SUPPORTED_INVERTERS[ds.InverterModel](ds.LogDetail, ds.InverterNode)

if ds.Estimate != '' and ds.bmsModel != '':
    if inverter.icEnergyUse.upper() in {txtUTI, txtSUB}:
        tp = int((ds.TargetPower + ds.MaxPowerLimit) / 2)
        lp = ds.LowPower
    else:
        tp = ds.TargetPower
        lp = int((ds.LowPower + ds.MinPower) / 2) # if b.bSOC < 50 else ds.MinPower
    sc = Solcast(ds, ds.MaxPowerLimit, tp, lp, ds.MinPower, ds.GridTied, ds.LogDetail)
    sc.Calculate(datetime.now(timezone.utc), ds.Estimate, 80, inverter.icMaxChargePower)
    be = inverter.setBestEnergySOC(sc.TargetDetected, sc.LowDetected, sc.MinDetected)
    inverter.Log(logDebug, f"Best energy result {be}")
elif ds.SolarVoltageOn > 1 or ds.SolarVoltageOff > 1:
    inverter.setBestEnergyPVV(ds.SolarVoltageOn, ds.SolarVoltageOff)

# todo: charge from grid if midnight (0..5am) and battery depleted

json_body = inverter.jSON()
inverter.Log(logDebug, json_body)
if platform.system() == "Linux": # switch it off when running on non-linux system for debug and test purposes
    ds.write(json_body)

    if ds.bmsModel != "" and ds.InverterModel == "Axioma": # workaround for Axioma inverter inability to properly manage LiFePo4 battery charging voltage
        if ds.GridChargingEnabled in [txtGCAlways, txtGCEmergency] or ("-" in ds.GridChargingEnabled and timeInRange(ds.GridChargingEnabled)):
            if ds.Estimate != '' or ds.GridChargingEstimate != '':
                gridChargingEstimate = ds.GridChargingEstimate if ds.GridChargingEstimate != "" else ds.Estimate
                sc.Calculate(datetime.now(timezone.utc), gridChargingEstimate, 80, inverter.icMaxChargePower)
                if sc.LowDetected is None or (sc.TargetDetected is not None and sc.TargetDetected < sc.LowDetected): # we can live on solar (optimistic or realistic)
                    inverter.setGridCharging(txtOSO, ds.MinUtiChargeCurent) # OSO, 2A
                else:
                    maxUtiChargeCurent = ds.MaxUtiChargeCurent
                    inverter.Log(logDebug, f"B {b.bBalance} CP {currentPower:.1f} TP {ds.TargetPower} UCC {maxUtiChargeCurent}")
                    if sc.MinDetected is not None and sc.TargetDetected is None:
                        inverter.setGridCharging(txtSNU, maxUtiChargeCurent) # SNU, 20A
                    else:
                        inverter.setGridCharging(txtCSO, maxUtiChargeCurent) # though would be good to calculate current based on electricity availability schedule
                tp = ds.TargetPower if sc.MinDetected else ds.TargetPower - ds.MaxPowerLimit + ds.TargetPower
            else:
                tp = ds.TargetPower
                inverter.setGridCharging(txtSNU if ds.GridChargingEnabled in [txtGCAlways] else txtCSO, ds.MaxUtiChargeCurent)
        elif ds.GridChargingEnabled == txtGCNoSolar:
            inverter.setGridCharging(txtCSO, ds.MaxUtiChargeCurent)
            tp = ds.TargetPower
        else:
            inverter.setGridCharging(txtOSO, ds.MinUtiChargeCurent)
            tp = ds.TargetPower

        if ds.PrecariousChargingEnabled: # todo: if protection kicks in, decrease bulk voltage by .1v; increase it by .1 v if no charge current, no balancing and not yet at the target, that may require also decreasing charging current
            equalized = b.bBalance == "" # overbalancing hurts # todo: implement timeout for balancing
            inverter.Log(logDebug, f"Precarious {tp} {currentPower} {ds.MaxPowerLimit}Wh PV {inverter.pvChargerPower}W {inverter.icChargerSourcePriority} EQ:{b.bBalance} {equalized} {ds.GridChargingFloat} {inverter.ccBatteryFloatVoltage} {ds.GridChargingBulk}V {b.bCurrent}A")
            if currentPower < tp and inverter.iBatteryVoltage <= ds.GridChargingFloat and (inverter.pvChargerPower > 1 or inverter.icChargerSourcePriority != txtOSO) and inverter.ccBatteryFloatVoltage < ds.GridChargingBulk:
                inverter.Log(logDebug, f"Charging start {currentPower:.1f}<{tp}W {inverter.pvChargerPower:.1f}>1W {inverter.icChargerSourcePriority}")
                inverter.setFloat(ds.GridChargingBulk) # 27.9 makes 100% sharply, 27.8 up to 91% charge
                # use SNU for 27.8 and then decrease current to 2 or 10A until reach target
            elif inverter.iBatteryVoltage >= ds.GridChargingBulk and b.bCurrent <= 0.0:
                inverter.Log(logDebug, f"Charging protection {inverter.iBatteryVoltage}V {b.bCurrent:.1f}A")
                inverter.setFloat(ds.GridChargingFloat)
            elif currentPower >= tp and b.bCurrent <= 0.0 and equalized and inverter.ccBatteryFloatVoltage > ds.GridChargingFloat: #bms current is reverse; wait until balanced
                inverter.Log(logDebug, f"Charging complete {currentPower:.1f}>{tp}W {b.bCurrent:.1f}A")
                inverter.setFloat(ds.GridChargingFloat)
            elif currentPower >= ds.MaxPowerLimit and inverter.ccBatteryFloatVoltage > ds.GridChargingFloat: #  and equalized:
                inverter.Log(logDebug, f"Charging limit {currentPower:.1f}>={ds.MaxPowerLimit}W")
                inverter.setFloat(ds.GridChargingFloat)
            elif inverter.pvVoltage < ds.SolarVoltageOff and inverter.pvChargerPower <= 0 and inverter.icChargerSourcePriority == txtOSO and inverter.ccBatteryFloatVoltage > ds.GridChargingFloat:
                inverter.Log(logDebug, f"Charging stop {inverter.pvChargerPower:.1f}<=0W {inverter.icChargerSourcePriority}")
                inverter.setFloat(ds.GridChargingFloat)

    elif ds.InverterModel == "GreenCell": # workaround for GreenCell inverter inability to properly charge battery from grid
        if ds.GridChargingEnabled in [txtGCAlways, txtGCEmergency] or ("-" in ds.GridChargingEnabled and timeInRange(ds.GridChargingEnabled)):
            inverter.Log(logDebug, f"GCC {ds.GridChargingFloat} {inverter.iBatteryVoltage} {ds.GridChargingBulk}V {inverter.iRadiatorTemperature} {inverter.rpiTemperature}C {inverter.icChargerSourcePriority} {inverter.pvVoltage}V")
            #if inverter.iBatteryVoltage <= 13.0 and inverter.iBattPower <= 0: # honestly SNU is not working for this inverter
            #    inverter.setSNU()
            if inverter.iBatteryVoltage < ds.GridChargingFloat and inverter.iBattPower <= 0 and inverter.pvVoltage < 14 and inverter.icChargerSourcePriority == txtOSO:
                inverter.setCSO() # todo: not to trigger it on discharging - measue when battery is calm
            elif inverter.iBatteryVoltage >= ds.GridChargingBulk and inverter.iRadiatorTemperature < inverter.rpiTemperature:
                inverter.setOSO()
                if ds.PrecariousChargingEnabled and inverter.ccBatteryFloatVoltage > ds.GridChargingFloat:
                    inverter.setFloat(ds.GridChargingFloat)
            elif ds.PrecariousChargingEnabled and inverter.iBatteryVoltage < ds.GridChargingFloat and inverter.pvVoltage < 14 and inverter.icChargerSourcePriority != txtOSO:
                inverter.setFloat(ds.GridChargingBulk) # better set SNU/CSO
            elif ds.PrecariousChargingEnabled and inverter.pvVoltage >= 14 and inverter.icChargerSourcePriority != txtSNU:
                inverter.setFloat(ds.GridChargingFloat)
            elif ds.PrecariousChargingEnabled and inverter.iGridVoltage < 100 and inverter.ccBatteryFloatVoltage > ds.GridChargingFloat:
                inverter.setFloat(ds.GridChargingFloat)
        elif ds.GridChargingEnabled == txtGCNoSolar:
            inverter.setCSO()
        else:
            inverter.setOSO()
