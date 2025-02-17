import time
from gpiozero import CPUTemperature
from . import Sample, UPS

def bitmaskText(newLine, Bitmask, Texts):
        t = ""
        for b in Texts:
            if b & Bitmask:
                if t != "":
                    t = t + ", "
                t = t + Texts[b]
        if bool(newLine and t != ""):
            return ", " + t
        else:
            return t   

def bitmaskNegative(value):
    if value > 32768:
        return value - 65536
    else:
        return value

class GreenCell(UPS):
    
    def __init__(self, device_path: str):
        super().__init__(device_path, 4, 19200)

    def sample(self, isDebug: bool) -> Sample:
      
      pvErrors = {
            1: "Hardware protection",
            2: "Over current",
            4: "Current sensor error",
            8: "Over temperature",
            16: "PV voltage is too high",
            32: "PV voltage is too low",
            64: "Battery voltage is too high",
            128: "Battery voltage is too Low",
            256: "Current is uncontrollable",
            512: "Parameter error",
            1024: "Unknown Error 10",
            2048: "Unknown Error 11",
            4096: "Unknown Error 12",
            8192: "Unknown Error 13",
            16384: "Unknown Error 14",
            32768: "Unknown Error 15"
      }
      pvWarnings = {
            1: "Fan Error",
            2: "Unknown Warning 1",
            4: "Unknown Warning 2",
            8: "Unknown Warning 3",
            16: "Unknown Warning 4",
            32: "Unknown Warning 5",
            64: "Unknown Warning 6",
            128: "Unknown Warning 7",
            256: "Unknown Warning 8",
            512: "Unknown Warning 9",
            1024: "Unknown Warning 10",
            2048: "Unknown Warning 11",
            4096: "Unknown Warning 12",
            8192: "Unknown Warning 13",
            16384: "Unknown Warning 14",
            32768: "Unknown Warning 15"
      }

      iError1s = {
        1: "Fan is locked when inverter is off",
        2: "Inverter transformer over temperature",
        4: "battery voltage is too high",
        8: "battery voltage is too low",
        16: "Output short circuited",
        32: "Inverter output voltage is high",
        64: "Overload time out",
        128: "Inverter bus voltage is too high",
        256: "Bus soft start failed",
        512: "Main relay failed",
        1024: "Inverter output voltage sensor error",
        2048: "Inverter grid voltage sensor error",
        4096: "Inverter output current sensor error",
        8192: "Inverter grid current sensor error",
        16384: "Inverter load current sensor error",
        32768: "Inverter grid over current error"
      }
      iError2s = {
        1: "Inverter radiator over temperature",
        2: "Solar charger battery voltage class error",
        4: "Solar charger current sensor error",
        8: "Solar charger current is uncontrollable",
        16: "Inverter grid voltage is low",
        32: "Inverter grid voltage is high",
        64: "Inverter grid under frequency",
        128: "Inverter grid over frequency",
        256: "Inverter over current protection error",
        512: "Inverter bus voltage is too low",
        1024: "Inverter soft start failed",
        2048: "Over DC voltage in AC output",
        4096: "Battery connection is open",
        8192: "Inverter control current sensor error",
        16384: "Inverter output voltage is too low",
        32768: "Unknown Error 2-15"
      }
      iError3s = {
        1: "Unknown Error 3-0",
        2: "Unknown Error 3-1",
        4: "Unknown Error 3-2",
        8: "Unknown Error 3-3",
        16: "Unknown Error 3-4",
        32: "Unknown Error 3-5",
        64: "Unknown Error 3-6",
        128: "Unknown Error 3-7",
        256: "Unknown Error 3-8",
        512: "Unknown Error 3-9",
        1024: "Unknown Error 3-10",
        2048: "Unknown Error 3-11",
        4096: "Unknown Error 3-12",
        8192: "Unknown Error 2-13",
        16384: "Unknown Error 2-14",
        32768: "Unknown Error 3-15"
      }

      iWarning1s = {
        1: "Fan is locked when inverter is on",
        2: "Fan2 is locked when inverter is on",
        4: "Battery is over-charged",
        8: "Low battery",
        16: "Overload",
        32: "Output power derating",
        64: "Solar charger stops due to low battery",
        128: "Solar charger stops due to high PV voltage",
        256: "Solar charger stops due to over load",
        512: "Solar charger over temperature",
        1024: "PV charger communication error",
        2048: "Unknown Warning 3-11",
        4096: "Unknown Warning 3-12",
        8192: "Unknown Warning 2-13",
        16384: "Unknown Warning 2-14",
        32768: "Unknown Warning 3-15"
      }
      iWarning2s = {
        1: "Unknown Warning 2-0",
        2: "Unknown Warning 2-1",
        4: "Unknown Warning 2-2",
        8: "Unknown Warning 2-3",
        16: "Unknown Warning 2-4",
        32: "Unknown Warning 2-5",
        64: "Unknown Warning 2-6",
        128: "Unknown Warning 2-7",
        256: "Unknown Warning 2-8",
        512: "Unknown Warning 2-9",
        1024: "Unknown Warning 2-10",
        2048: "Unknown Warning 2-11",
        4096: "Unknown Warning 2-12",
        8192: "Unknown Warning 2-13",
        16384: "Unknown Warning 2-14",
        32768: "Unknown Warning 2-15"
      }

      inverterWorkStates = {
        0: "Power On", 
        1: "Self Test", 
        2: "Off Grid", 
        3: "Grid-Tie", 
        4: "ByPass", 
        5: "Stop", 
        6: "Grid charging"
      }
      pvWorkStates = {
        0: "Initialization",    # "Initialization mode", 
        1: "Selftest",          # "Selftest Mode", 
        2: "Work",              # "Work Mode", 
        3: "Stop",              # "Stop Mode"
      }
      mpptStates = {
        0: "S",                 # "Stop", 
        1: "MPPT", 
        2: "CL"                 # "Current limiting"
      }
      chargingStates = {
        0: "S",                 # "Stop", 
        1: "A",                 # "Absorb charge", 
        2: "F",                 # "Float charge", 
        3: "EQ",                # "EQ charge"
      }
      relayStates = { 0: "Off", 1: "ON" }

      icEnergyUses = { 1: "SBU", 2: "SUB", 3: "UTI", 4: "SOL"}
      icSolarUseAims = { 0: "LBU", 1: "BLU" }

      self.scc.debug = isDebug
      ic = self.scc.read_registers(20100, 45)
      if isDebug:
        print("iControl Message: ", ic)
                                               # 20101	RW	Inverter offgrid work enable	0：OFF 1：ON  
                                               # 20102	RW	Inverter output voltage Set	220.0V-240.0V
                                               # 20103	RW	Inverter output frequency Set	50.00Hz/60.00Hz
                                               # 20104	RW	Inverter search mode enable	0：OFF 1：ON  
                                               # 20108	RW	Inverter discharger to grid enable	"48V:   0：OFF  1：ON 24V:  Null"
      icEnergyUse = icEnergyUses[ic[9]]        # 20109	RW	Energy use mode	"48V:1:SBU;2:SUB;3:UTI;4:SOL (for PV;PH) |  1:BAU; 3:UTI;4:BOU (for EP) | 12V 24V:1:SBU;;3:UTI;4:SOL (for PV;PH) | 1:BU; 3:UTI (for EP)
                                               # 20111	RW	Grid protect standard	0：VDE4105; 1：UPS  ;  2：home ;3:GEN
      #icSolarUseAim = icSolarUseAims[ic[12]]   # 20112	RW	SolarUse Aim	"0:LBU  1:BLU(defalut)(for PV;PH) | 0:LB  1:LU(defalut)  (for EP)"
                                               # 20113	RW	Inverter max discharger current	"48V:  0.1A（AC）| 12V 24V:  Null"
      icBatteryStopDischarging = ic[18] / 10.0 # 20118	RW	Battery stop discharging voltage	0.1V  
      icBatteryStopCharging = ic[19] / 10.0    # 20119	RW	Battery stop charging voltage	0.1V  
                                               # 20125	RW	Grid max charger current set	0.1A(DC)
                                               # 20127	RW	Battery low voltage	0.1V
                                               # 20128	RW	Battery high voltage	0.1V
                                               # 20132	RW	Max Combine charger current	0.1A(DC)(for PV;PH)
                                               # 20142	RW	System setting	
                                               # 20143	RW	Charger source priority	"0:Soalr first  (for PV;PH) | 2:Solar and Utility(default)  (for PV;PH) | 3:Only Solar  (for PV;PH) | 2:Utility charger enable (default)  (for EP) 3:Utility charger disable   (for EP)
                                               # 20144	RW	Solar power balance	"0:SBD 1:SBE"

      time.sleep(0.02)
      pv = self.scc.read_registers(15200, 22)
      if isDebug:
        print("PV Message: ", pv)
      if pv[1]==2: # work mode
          pvWorkState = mpptStates[pv[2]] + "-" + chargingStates[pv[3]]   # 15201 15202 15203
      else:
          pvWorkState = pvWorkStates[pv[1]]                               # 15201 15202 15203
      pvVoltage = pv[5] / 10.0                               # 15205
      pvBatteryVoltage = pv[6] / 10.0                        # 15206
      pvChargerCurrent = pv[7] / 10.0	                     # 15207
      pvChargerPower = pv[8]	                             # 15208
      pvRadiatorTemperature = pv[9]                          # 15209
      pvBatteryRelay = relayStates[pv[11]]                   # 15211
      pvRelay = relayStates[pv[12]]                          # 15212
      pvError = bitmaskText(False, pv[13], pvErrors)         # 15213
      pvWarning = bitmaskText(False, pv[14], pvWarnings)     # 15214
      pvAccumulatedPower = (pv[17] * 1000) + (pv[18] / 10.0) # 15217 mWh, 15218  .1KWh
          
      time.sleep(0.02)
      soc = self.scc.read_registers(25200, 75)
      if isDebug:
        print("Invertor Message: ", soc)
       
      iWorkState = inverterWorkStates[soc[1]]         # 25201
      iBatteryVoltage = soc[5] / 10.0                 # 25205: ["Battery voltage", 0.1, "V"],        
      iVoltage = soc[6] / 10.0                        # 25206: ["Inverter voltage", 0.1, "V"],
      iGridVoltage = soc[7] / 10.0                    # 25207: ["Grid voltage", 0.1, "V"],
                                                      # 25208: ["BUS voltage", 0.1, "V"],
                                                      # 25209: ["Control current", 0.1, "A"],
                                                      # 25210: ["Inverter current", 0.1, "A"],
                                                      # 25211: ["Grid current", 0.1, "A"],
                                                      # 25212: ["Load current", 0.1, "A"],
      iPInverter = soc[13]	                          # 25213: ["Inverter power(P)", 1, "W"],
      iPGrid = soc[14]                                # 25214: ["Grid power(P)", 1, "W"],
      iPLoad = soc[15]                                # 25215: ["Load power(P)", 1, "W"],
      iLoadPercent = soc[16]                          # 25216: ["Load percent", 1, "%"],
      iSInverter = soc[17]                            # 25217: ["Inverter complex power(S)", 1, "VA"],
      iSGrid = soc[18]                                # 25218: ["Grid complex power(S)", 1, "VA"],
      iSLoad = soc[19]                                # 25219: ["Load complex power(S)", 1, "VA"],
                                                      # 25221: ["Inverter reactive power(Q)", 1, "var"],
                                                      # 25222: ["Grid reactive power(Q)", 1, "var"],
                                                      # 25223: ["Load reactive power(Q)", 1, "var"],
                                                      # 25225: ["Inverter frequency", 0.01, "Hz"],
                                                      # 25226: ["Grid frequency", 0.01, "Hz"],       
      iRadiatorTemperature = soc[33]                  # 25233: ["AC radiator temperature", 1, "°C"],
                                                      # 25234: ["Transformer temperature", 1, "°C"],
                                                      # 25235: ["DC radiator temperature", 1, "°C"],
      iRelayState = relayStates[soc[37]]              # 25237: ["Inverter relay state", 1, ""],
      iGridRelayState = relayStates[soc[38]]          # 25238: ["Grid relay state", 1, ""],
      iLoadRelayState = relayStates[soc[39]]          # 25239: ["Load relay state", 1, ""],
                                                      # 25240: ["N_Line relay state", 1, ""],
                                                      # 25241: ["DC relay state", 1, ""],
                                                      # 25242: ["Earth relay state", 1, ""],
                                                      # 25245: ["Accumulated charger power high", 1000, "kWh"],
                                                      # 25246: ["Accumulated charger power low", 0.1, "kWh"],
      iAccumulatedDischargerPower = (soc[47] * 1000) + (soc[48] / 10.0) # 25247: ["Accumulated discharger power high", 1000, "kWh"],
                                                      # 25248: ["Accumulated discharger power low", 0.1, "kWh"],
                                                      # 25249: ["Accumulated buy power high", 1, "kWh"],
                                                      # 25250: ["Accumulated buy power low", 0.1, "kWh"],
                                                      # 25251: ["Accumulated sell power high", 1, "kWh"],
                                                      # 25252: ["Accumulated sell power low", 0.1, "kWh"],
      iAccumulatedLoadPower = (soc[53] * 1000) + (soc[54] / 10.0)  # 25253: ["Accumulated load power high", 1, "kWh"],
                                                      # 25254: ["Accumulated load power low", 0.1, "kWh"],
      iAccumulatedSelfusePower = (soc[55] * 1000) + (soc[56] / 10.0 )    # 25255: ["Accumulated self_use power high", 1000, "kWh"],
                                                      # 25256: ["Accumulated self_use power low", 0.1, "kWh"],
                                                      # 25257: ["Accumulated PV_sell power high", 1, "kWh"],
                                                      # 25258: ["Accumulated PV_sell power low", 0.1, "kWh"],
                                                      # 25259: ["Accumulated grid_charger power high", 1, "kWh"],
                                                      # 25260: ["Accumulated grid_charger power low", 0.1, "kWh"],
      iError = bitmaskText(False, soc[61], iError1s)            # 25261	Error message 1
      iError += bitmaskText(iError != "", soc[62], iError2s)    # 25262	Error message 2
      iError += bitmaskText(iError != "", soc[63], iError3s)    # 25263	Error message 3
      iWarning = bitmaskText(False, soc[65], iWarning1s)           # 25265	Warning message 1
      iWarning += bitmaskText(iWarning != "", soc[66], iWarning2s) # 25266	Warning message 2
                                                      # 25271: ["Hardware version", 1, ""],
                                                      # 25272: ["Software version", 1, ""],
      iBattPower = bitmaskNegative(soc[73])           # 25273: ["Battery power", 1, "W"],
      iBattCurrent = bitmaskNegative(soc[74])         # 25274: ["Battery current", 1, "A"],

      rpiTemperature = CPUTemperature().temperature

      return Sample( icEnergyUse, icBatteryStopDischarging, icBatteryStopCharging, 0,
        pvWorkState, pvVoltage, pvBatteryVoltage, pvChargerCurrent, pvChargerPower, 
        pvRadiatorTemperature, pvBatteryRelay, pvRelay, pvError, pvWarning, pvAccumulatedPower,
        iWorkState, iBatteryVoltage, iVoltage, iGridVoltage, iPInverter, iPGrid, iPLoad, iLoadPercent, iSInverter, 
        iSGrid, iSLoad, iRadiatorTemperature, iRelayState, iGridRelayState, iLoadRelayState, iAccumulatedLoadPower, 
        iAccumulatedDischargerPower, iAccumulatedSelfusePower, iError, iWarning, iBattPower, iBattCurrent,
        rpiTemperature
      )
  
    def setSolar(self, isDebug: bool):
        if isDebug:
            print("set Solar")
        time.sleep(0.1) # just in case
        self.scc.write_register(20109, 1)  # 20109	RW	Energy use mode	"48V:1:SBU;2:SUB;3:UTI;4:SOL (for PV;PH) |  1:BAU; 3:UTI;4:BOU (for EP) | 12V 24V:1:SBU;;3:UTI;4:SOL (for PV;PH) | 1:BU; 3:UTI (for EP)

    def setUtility(self, isDebug: bool):
        if isDebug:
            print("set Utility")
        time.sleep(0.1) # just in case
        self.scc.write_register(20109, 3) # 20109	RW	Energy use mode	"48V:1:SBU;2:SUB;3:UTI;4:SOL (for PV;PH) |  1:BAU; 3:UTI;4:BOU (for EP) | 12V 24V:1:SBU;;3:UTI;4:SOL (for PV;PH) | 1:BU; 3:UTI (for EP)

