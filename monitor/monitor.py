from datetime import datetime, timezone
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

ds = DataStore() # initialize datastore to read settings and connect to database

if ds.bmsModel in SUPPORTED_BMS: # initialize BMS if configured, read data and write to database
    b: bms = SUPPORTED_BMS[ds.bmsModel](ds.LogDetail, ds.bmsNode)
    json_body = b.jSON()
    b.Log(logDebug, json_body)
    ds.write(json_body)
    bmsSOC = b.bSOC
elif ds.bmsModel != "": # if BMS model is not empty but unsupported, print error and exit
    print(f"Error: Unknown BMS model: {ds.bmsModel}")
    exit(1)
else: # no BMS configured, set SOC to -1 to indicate unknown state
    bmsSOC = -1

if ds.InverterModel not in SUPPORTED_INVERTERS:
    print(f"Error: Unknown inverter model: {ds.InverterModel}")
    exit(1)

inverter: inverterMgr = SUPPORTED_INVERTERS[ds.InverterModel](ds.LogDetail, ds.InverterNode)

if ds.Estimate != '':
    if inverter.icEnergyUse.upper() in {txtUTI, txtSUB}:
        tp = int((ds.TargetPower + ds.MaxPowerLimit) / 2)
        lp = ds.LowPower
    else:
        tp = ds.TargetPower
        lp = int((ds.LowPower + ds.MinPower) / 2) # if b.bSOC < 50 else ds.MinPower
    sc = Solcast(ds, ds.MaxPowerLimit, tp, lp, ds.MinPower, ds.GridTied, ds.LogDetail)
    sc.Calculate(datetime.now(timezone.utc), ds.Estimate, 80)
    be = inverter.setBestEnergySOC(sc.TargetDetected, sc.LowDetected, sc.MinDetected)
    inverter.Log(logDebug, f"{datetime.now()} Best energy result {be}")
elif ds.SolarVoltageOn > 1 or ds.SolarVoltageOff > 1:
    inverter.setBestEnergyPVV(ds.SolarVoltageOn, ds.SolarVoltageOff)

# todo: charge from grid if midnight (0..5am) and battery depleted
 
json_body = inverter.jSON()
inverter.Log(logDebug, json_body)
if ds.InverterNode != "SIMULATOR":
    ds.write(json_body)

if ds.InverterNode != "SIMULATOR":
    gridChargingEnabled = ds.GridChargingEnabled == txtGCAlways # todo: add option to parse time range i.e. 23:00-07:00 etc
    if ds.bmsNode != "SIMULATOR" and ds.InverterModel == "Axioma": # workaround for Axioma inverter inability to properly manage battery charging voltage
        currentPower = b.CurrentPower
        if gridChargingEnabled:
            if ds.Estimate != '' or ds.GridChargingEstimate != '':
                gridChargingEstimate = ds.GridChargingEstimate if ds.GridChargingEstimate != "" else ds.Estimate
                sc.Calculate(datetime.now(timezone.utc), gridChargingEstimate, 80)
                if sc.LowDetected is None or (sc.TargetDetected is not None and sc.TargetDetected < sc.LowDetected): # we can live on solar (optimistic or realistic)
                    if inverter.icChargerSourcePriority != txtOSO or inverter.icMaxUtiChargeCurrent != 2:
                        inverter.setGridCharging(txtOSO, 2) # OSO, 2A
                else:
                    maxUtiChargeCurent = 20
                    inverter.Log(logDebug, f"B {b.bBalance} CP {currentPower:.1f} TP {ds.TargetPower} UCC {maxUtiChargeCurent}")
                    if sc.MinDetected is not None and sc.TargetDetected is None:
                        if inverter.icChargerSourcePriority != txtSNU or inverter.icMaxUtiChargeCurrent != maxUtiChargeCurent:
                            inverter.setGridCharging(txtSNU, maxUtiChargeCurent) # SNU, 20A
                    else:
                        if inverter.icChargerSourcePriority != txtCSO or inverter.icMaxUtiChargeCurrent != maxUtiChargeCurent:
                            inverter.setGridCharging(txtCSO, maxUtiChargeCurent) # though would be good to calculate current based on electricity availability schedule
                tp = ds.TargetPower if sc.MinDetected else ds.TargetPower - ds.MaxPowerLimit + ds.TargetPower
            else:
                tp = ds.TargetPower
        else:
            inverter.setGridCharging(txtOSO, 2)

        if ds.PrecariousChargingEnabled:
            equalized = True # overbalancing hurts b.bBalance == "" # todo: implement timeout for balancing
            if currentPower < tp and (inverter.pvChargerPower > 0 or inverter.icChargerSourcePriority != txtOSO) and inverter.ccBatteryFloatVoltage < ds.GridChargingBulk:
                inverter.Log(logDebug, f"Charging start {currentPower:.1f}<{tp}W {inverter.pvChargerPower:.1f}>0W {inverter.icChargerSourcePriority}")
                inverter.setFloat(ds.GridChargingBulk) # 27.9 makes 100% sharply, 27.8 up to 91% charge
                # use SNU for 27.8 and then decrease current to 2 or 10A until reach target
            elif currentPower > tp and b.bCurrent <= 0 and equalized and inverter.ccBatteryFloatVoltage > ds.GridChargingFloat: #bms current is reverse; wait until balanced
                inverter.Log(logDebug, f"Charging complete {currentPower:.1f}>{tp}W {b.bCurrent:.1f}A")
                inverter.setFloat(ds.GridChargingFloat)
            elif currentPower >= ds.MaxPowerLimit and equalized and inverter.ccBatteryFloatVoltage > ds.GridChargingFloat:
                inverter.Log(logDebug, f"Charging limit {currentPower:.1f}>={ds.MaxPowerLimit}W")
                inverter.setFloat(ds.GridChargingFloat)
            elif inverter.pvChargerPower <= 0 and inverter.icChargerSourcePriority != txtOSO and inverter.ccBatteryFloatVoltage > ds.GridChargingFloat:
                inverter.Log(logDebug, f"Charging stop {inverter.pvChargerPower:.1f}<=0W {inverter.icChargerSourcePriority}")
                inverter.setFloat(ds.GridChargingFloat)

    elif ds.InverterModel == "GreenCell": # workaround for GreenCell inverter inability to properly charge battery from grid
        if gridChargingEnabled:
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
        else:
            inverter.setOSO()