from datetime import datetime
import platform
if __name__ == "_inverter_":
    from __init__ import device
    from _constants_ import *
else:
    from ups import device
    from ups._constants_ import *

class inverterMgr(device): # base class for smarter solar power and battery management (use most of solar but still save battery)
    def __init__(self, logDetail: int, **kwargs):
        super().__init__(logDetail = logDetail, **kwargs)
        self.measurement = "inverter"

        if platform.system() == "Linux": # read Raspberry CPU temperature
            try:
                with open('/sys/class/thermal/thermal_zone0/temp', 'r') as file:
                    self.rpiTemperature: float = round(float(file.read()) / 1000.0, 1)
            except:
                self.rpiTemperature: float = 0.0
        else:
            self.Log(logWarning, f"Platform is {platform.system()}")
            self.rpiTemperature: float = 0.0

        self.ccBatteryFloatVoltage: float = 0.0

        self.icEnergyUse: str = ""
        self.icSolarUseAim: str = ""
        self.icBatteryStopDischarging: float = 0.0
        self.icBatteryStopCharging: float = 0.0
        self.icBatteryEqualization: float = 0.0
        self.icChargerSourcePriority: str = ""
        self.icMaxUtiChargeCurrent: int = 0
        self.icMaxChargeCurrent: int = 0

        self.pvWorkState: str = ""
        self.pvVoltage: float = 0.0
        self.pvBatteryVoltage: float = 0.0
        self.pvChargerCurrent: float = 0.0
        self.pvChargerPower: int = 0
        self.pvRadiatorTemperature: int = 0
        self.pvError: str = ""
        self.pvWarning: str = ""
        self.pvAccumulatedPower: float = 0.0
        self.pvReturnGrid: int = 0

        self.iWorkState: str =""
        self.iBatteryVoltage: float = 0.0
        self.iVoltage: float = 0.0
        self.iGridVoltage: float = 0.0
        self.iPInverter: int = 0
        self.iPGrid: int = 0
        self.iPLoad: int = 0
        self.iLoadPercent: int = 0
        self.iSInverter: int = 0
        self.iSGrid: int = 0
        self.iSLoad: int = 0
        self.iRadiatorTemperature: int = 0
        self.iAccumulatedLoadPower: float = 0.0
        self.iAccumulatedDischargerPower: float = 0.0
        self.iAccumulatedSelfusePower: float = 0.0
        self.iError:  str = ""
        self.iWarning: str = ""
        self.iBattPower: int = 0
        self.iBattCurrent: int = 0

        self.BestEnergyMsg: str = ""
        self.BatteryVoltageGrade: float = 0.0

    @property
    def icMaxChargePower(self) -> int:
        return int(self.icMaxChargeCurrent * self.BatteryVoltageGrade * 16 / 15) # 12V LiFePo4 rated 12.8, 24 is 25.6, 48 is 51.2

    def _getMandatoryFields_(self) -> dict:
        return {
            "pvVoltage": self.pvVoltage,
            "pvChargerCurrent": self.pvChargerCurrent, 
            "pvChargerPower": self.pvChargerPower,
            "iBatteryVoltage": self.iBatteryVoltage,
            "iGridVoltage": self.iGridVoltage,
            "iPGrid": self.iPGrid,
            "iPLoad": self.iPLoad,
            "iPInverter": self.iPInverter,
            "iBattPower": self.iBattPower,
            "iBattCurrent": self.iBattCurrent
        }
    def _getOptionalValues_(self) -> list:
        return [
            ("icEnergyUse", ''),
            ("icSolarUseAim", ''),
            ("pvWorkState", ''),
            ("pvBatteryVoltage", 0.0),
            ("pvRadiatorTemperature", 0),
            ("pvAccumulatedPower", 0),
            ("pvError", ''),
            ("pvWarning", ''),
            ("iWorkState", ''),
            ("iVoltage", 0.0),
            ("iLoadPercent", 0),
            ("iSInverter", 0),
            ("iSGrid", 0),
            ("iSLoad",  0),
            ("iRadiatorTemperature", 0),
            ("iAccumulatedLoadPower", 0.0),
            ("iAccumulatedDischargerPower", 0.0),
            ("iAccumulatedSelfusePower", 0.0),
            ("iError", ''),
            ("iWarning", ''),
            ("rpiTemperature", 0),
            ("tRadiatorTemperature", 0),
            ("bRadiatorTemperature", 0),
            ("pvReturnGrid", 0),
            ("icChargerSourcePriority", ""),
            ("BestEnergyMsg", "")
        ]

    def setSBU(self):
        if self.icEnergyUse != txtSBU:
            self.Log(logWrite, "set SBU")
            return True
        else:
            return False

    def setSUB(self):
        if self.icEnergyUse != txtSUB:
            self.Log(logWrite, "set SUB")
            return True
        else:
            return False

    def setUtility(self):
        if self.icEnergyUse != txtUTI:
            self.Log(logWrite, "set UTI")
            return True
        else:
            return False

    def setCSO(self):
        if self.icChargerSourcePriority != txtCSO:
            self.Log(logWrite, "set CSO")
            return True
        else:
            return False

    def setSNU(self):
        if self.icChargerSourcePriority != txtSNU:
            self.Log(logWrite, "set SNU")
            return True
        else:
            return False

    def setOSO(self):
        if self.icChargerSourcePriority != txtOSO:
            self.Log(logWrite, "set OSO")
            return True
        else:
            return False

    def moreSolar(self):
        self.Log(logDebug, self.BestEnergyMsg)
        return self.setOSO()

    def saveBattery(self, intenseCharge: bool = False):
        self.Log(logDebug, f"Save Battery {self.BestEnergyMsg} {intenseCharge}")
        if intenseCharge:
            return self.setSNU()
        else:
            return self.setOSO()

    def setFloat(self, voltage: float):
        if self.ccBatteryFloatVoltage != voltage:
            self.Log(logWrite, f"set FLoat {voltage}V")
            return True
        else:
            return False

    def setGridChargingCurrent(self, current: int):
        if self.icMaxUtiChargeCurrent != current:
            self.Log(logWrite, f"set Grid Charging {current}A")
            return True
        else:
            return False

    def setGridCharging(self, mode: str, current: int):
        if self.icMaxUtiChargeCurrent != current or self.icChargerSourcePriority != mode:
            self.Log(logWrite, f"set Grid Charging {mode} {current}A (was {self.icChargerSourcePriority} {self.icMaxUtiChargeCurrent}A)")
            return True
        else:
            return False

    # todo: Solar Use Aim LBU - BLU depending on battery SOC and future estimate
    # todo: Charger source priority OSO - SNU - CSO depending on battery SOC and tomorrow estimate

    def setBestEnergySOC(self, TargetDetected: datetime, LowDetected: datetime, MinDetected: datetime):
        if TargetDetected is not None and (LowDetected is None or TargetDetected < LowDetected):
            self.Log(logDebug, f"Target level shall be reached first at {self.dtKyiv(TargetDetected)}, Low at {LowDetected}")
            if self.icEnergyUse.upper() in {txtUTI, txtSUB}:
                self.BestEnergyMsg = f"T {self.dtKyiv(TargetDetected)}"
                return 1 if self.setSBU() else 0
        elif LowDetected is not None:
            self.Log(logDebug, f"Low level could be reached first on {self.dtKyiv(LowDetected)}, Target on {TargetDetected}")
            if self.icEnergyUse.upper() in {txtSBU, txtSUB}:
                self.BestEnergyMsg = f"L {self.dtKyiv(LowDetected)}"
                if self.pvChargerPower < self.iPLoad:
                    if MinDetected is not None and (TargetDetected is None or MinDetected < TargetDetected):
                        self.BestEnergyMsg = self.addText(self.BestEnergyMsg, f"M {self.dtKyiv(MinDetected)}")
                        self.Log(logDebug, f"!!! Battery would be depleted below minimum on {self.dtKyiv(MinDetected)}")
                        return -1 if self.setUtility() else 0
                    else:
                        return -1 if self.setSUB() else 0
        if MinDetected is not None: # always show minimum if it was detected
            self.BestEnergyMsg = self.addText(self.BestEnergyMsg, f"M {self.dtKyiv(MinDetected)}")
        return None

    def setBestEnergyPVV(self, solarVoltageOn: float, solarVoltageOff: float):
        self.Log(logDebug, f"Check Solar Voltage {solarVoltageOff} > {self.pvVoltage} > {solarVoltageOn}")
        if self.icEnergyUse.upper() in {txtUTI, txtSUB}: # Utility or PV mixing mode
            if solarVoltageOn > 1 and self.iBatteryVoltage >= self.icBatteryStopCharging:
                if self.pvVoltage > solarVoltageOn: # and self.pvChargerPower > 0: # likely PV can produce more - however more sophisticated formula needed since voltage depends on power produced
                    self.BestEnergyMsg = f"ON {self.pvVoltage} > {solarVoltageOn} V"
                    return self.moreSolar()
                # todo: mind solar use aim LBU - BLU here
                elif self.icSolarUseAim == "LBU" and self.pvChargerPower > self.iPLoad and self.pvVoltage > solarVoltageOff: #+ self.iInternalUsePower: # PV produces enough just charging - technically charging can be delayed
                    self.BestEnergyMsg = f"ON {self.pvChargerPower} > {self.iPLoad} W"
                    return self.moreSolar()
            #elif : # more than equalization and pv > avg(on, off) meaning battery is overcharged
        elif self.icEnergyUse.upper() in {txtSBU, txtSUB}: # PV full production mode
            if solarVoltageOff > 1 and self.pvChargerPower < self.iPLoad: # solar power not enough
                solarVoltageOff = solarVoltageOff * (1 - (self.pvChargerPower / 10000)) # mind possible 1% drop for every 100W production
                if self.iBattCurrent > 0 and self.icBatteryStopCharging - self.icBatteryStopDischarging > 1: # mind 1V voltage drop under 50A high load for non-Li batteries
                    stopDischarge = self.icBatteryStopDischarging - (self.iBattCurrent / 50) 
                else:
                    stopDischarge = self.icBatteryStopDischarging
                if self.iPGrid >= self.iPLoad and self.iBatteryVoltage < (self.icBatteryStopCharging + stopDischarge) / 2: # working from Grid
                    self.BestEnergyMsg = f"Off Grid {self.iPGrid} >= Load {self.iPLoad} > PV {self.pvChargerPower} W & {self.iBatteryVoltage} < avg({self.icBatteryStopCharging} {stopDischarge:.2f}) V"
                    return self.saveBattery()  
                elif self.iBattPower > self.pvChargerPower and self.iBatteryVoltage <= stopDischarge: # depleting battery too much
                    self.BestEnergyMsg = f"Off Batt {self.iBattPower} > PV {self.pvChargerPower} < Load {self.iPLoad} W & {self.iBatteryVoltage} <= {stopDischarge:.2f} V"
                    return self.saveBattery()                    
                elif self.pvVoltage < solarVoltageOff: # better to be more sophisticated formula accounting MPPT since voltage depend on produced power
                    self.BestEnergyMsg = f"Off PV {self.pvVoltage} < {solarVoltageOff:.2f} V"
                    return self.saveBattery()
        return False

class inverterOffGrid(inverterMgr): # base class for off grid type invertors
    def moreSolar(self):
        #if self.pvChargerPower > self.iPLoad:
        #    if self.iBatteryVoltage > (self.icBatteryStopCharging + self.icBatteryStopDischarging) / 2:
        #        return super().moreSolar() and self.setSBU()
        #else:
        #    if self.iBatteryVoltage >= self.ccBatteryFloatVoltage: # still may  prevent going to battery by SOC
                return super().moreSolar() and self.setSBU()
    def saveBattery(self, intenseCharge: bool = False):
        return super().saveBattery(intenseCharge) and self.setUtility()

class inverterHybrid(inverterMgr): # base class for hybrid type invertors
    def moreSolar(self):
        self.Log(logDebug, f"More Solar {self.iBatteryVoltage} ~ avg({self.icBatteryStopCharging} {self.icBatteryStopDischarging}) V")
        if self.iBatteryVoltage > (self.icBatteryStopCharging + self.icBatteryStopDischarging) / 2:
            return super().moreSolar() and self.setSBU()
        else:
            return super().moreSolar() and self.setSUB()
    def saveBattery(self, intenseCharge: bool = False):
        self.Log(logDebug, f"Save Battery {self.iBatteryVoltage} ~ avg({self.icBatteryStopCharging} {self.icBatteryStopDischarging}) V")
        if self.iBatteryVoltage < (self.icBatteryStopCharging + self.icBatteryStopDischarging) / 2:
            return super().saveBattery(intenseCharge) and self.setUtility()
        else:
            return super().saveBattery(intenseCharge) and self.setSUB()

if __name__ == "__main__":
    i = inverterMgr(logDebug)
    i.icEnergyUse = "SBU"
    i.pvVoltage = 10
    i.pvChargerPower = 50
    i.iPLoad = 100
    i.iBattCurrent = 20
    i.icBatteryStopDischarging = 24
    i.icBatteryStopCharging = 29

    i.setBestEnergyPVV(70,30)
    i.Log(logDebug, i.jSON())