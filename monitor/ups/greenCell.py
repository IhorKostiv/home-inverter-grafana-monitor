from datetime import datetime
if __name__ == "__main__":
#    import re
    from __init__ import UPSmodbus, UPSoffgrid, addText
else:
    from . import UPSmodbus, UPSoffgrid, addText

def bitmaskNegative(value): # used to extract battery power and current values
    if value > 32768:
        return value - 65536
    else:
        return value

def bitmaskText(newLine, Bitmask, Texts): # used to convert error or warning bitmasks to text
        t = ""
        for b in Texts:
            if b & Bitmask == b:
                t = addText(t, Texts[b])
        return ", " + t if newLine and t != "" else t

class GreenCell(UPSmodbus, UPSoffgrid): #  object to communicate with and manage GreenCell inverter
    
    def __init__(self, isDebug: bool, device_path: str):
        super().__init__(isDebug, device_path, 4, 19200)

        self.readInverterControl()
        self.readPV()
        self.readInverter()

    def readRegister(self, register: int, length: int, debugMessage: str):
        if hasattr(self, 'scc'): # check if we are live in production or unit testing
            r = super().readRegister(register, length)
            #if self.isDebug:
            print(f"{datetime.now().strftime("%Y-%m-%d %H:%M")} {debugMessage}: {r}")
        else:
            if register in utMessages:
                r = utMessages[register]
            else:
                r = utRead(register)
        return r

    def readInverterControl(self): # read inverter control message values
        icEnergyUses = { 1: "SBU", 2: "SUB", 3: "UTI", 4: "SOL"}

        ic = self.readRegister(20100, 45, "iC")
                                               # 20101	RW	Inverter offgrid work enable	0：OFF 1：ON  
                                               # 20102	RW	Inverter output voltage Set	220.0V-240.0V
                                               # 20103	RW	Inverter output frequency Set	50.00Hz/60.00Hz
                                               # 20104	RW	Inverter search mode enable	0：OFF 1：ON  
                                               # 20108	RW	Inverter discharger to grid enable	"48V:   0：OFF  1：ON 24V:  Null"
        self.icEnergyUse = icEnergyUses[ic[9]] # 20109	RW	Energy use mode	"48V:1:SBU;2:SUB;3:UTI;4:SOL (for PV;PH) |  1:BAU; 3:UTI;4:BOU (for EP) | 12V 24V:1:SBU;;3:UTI;4:SOL (for PV;PH) | 1:BU; 3:UTI (for EP)
                                               # 20111	RW	Grid protect standard	0：VDE4105; 1：UPS  ;  2：home ;3:GEN
        #icSolarUseAim = icSolarUseAims[ic[12]] # 20112	RW	SolarUse Aim	"0:LBU  1:BLU(defalut)(for PV;PH) | 0:LB  1:LU(defalut)  (for EP)"
                                               # 20113	RW	Inverter max discharger current	"48V:  0.1A（AC）| 12V 24V:  Null"
        self.icBatteryStopDischarging = ic[18] / 10.0 # 20118	RW	Battery stop discharging voltage	0.1V  
        self.icBatteryStopCharging = ic[19] / 10.0    # 20119	RW	Battery stop charging voltage	0.1V  
                                               # 20125	RW	Grid max charger current set	0.1A(DC)
                                               # 20127	RW	Battery low voltage	0.1V
                                               # 20128	RW	Battery high voltage	0.1V
                                               # 20132	RW	Max Combine charger current	0.1A(DC)(for PV;PH)
                                               # 20142	RW	System setting	
                                               # 20143	RW	Charger source priority	"0:Soalr first  (for PV;PH) | 2:Solar and Utility(default)  (for PV;PH) | 3:Only Solar  (for PV;PH) | 2:Utility charger enable (default)  (for EP) 3:Utility charger disable   (for EP)
                                               # 20144	RW	Solar power balance	"0:SBD 1:SBE"
        return ic

    def readPV(self): # read PV message values
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
        pvWorkStates = {
            0: "Initialization",    # "Initialization mode", 
            1: "Selftest",          # "Selftest Mode", 
            2: "Work",              # "Work Mode", 
            3: "Stop"              # "Stop Mode"
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
            3: "EQ"                 # "EQ charge"
        }

        pv = self.readRegister(15200, 22, "PV")
        if pv[1]==2: # work mode                                    # 15201 15202 15203
            self.pvWorkState = mpptStates[pv[2]] + "-" + chargingStates[pv[3]]   
        else:
            self.pvWorkState = pvWorkStates[pv[1]]
        self.pvVoltage = pv[5] / 10.0                               # 15205
        self.pvBatteryVoltage = pv[6] / 10.0                        # 15206
        self.pvChargerCurrent = pv[7] / 10.0	                    # 15207
        self.pvChargerPower = pv[8]	                                # 15208
        self.pvRadiatorTemperature = pv[9]                          # 15209
        self.pvError = bitmaskText(False, pv[13], pvErrors)         # 15213
        self.pvWarning = bitmaskText(False, pv[14], pvWarnings)     # 15214
        self.pvAccumulatedPower = (pv[17] * 1000) + (pv[18] / 10.0) # 15217 mWh, 15218 .1 KWh
        return pv
  
    def readInverter(self): # read Inverter message values
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

        iWorkStates = {
        0: "Power On", 
        1: "Self Test", 
        2: "Off Grid", 
        3: "Grid-Tie", 
        4: "ByPass", 
        5: "Stop", 
        6: "Grid charging"
      }

        i = self.readRegister(25200, 75, "I")
       
        self.iWorkState = iWorkStates[i[1]] # 25201
        self.iBatteryVoltage = i[5] / 10.0  # 25205: ["Battery voltage", 0.1, "V"],
        self.iVoltage = i[6] / 10.0         # 25206: ["Inverter voltage", 0.1, "V"],
        self.iGridVoltage = i[7] / 10.0     # 25207: ["Grid voltage", 0.1, "V"],
                                            # 25208: ["BUS voltage", 0.1, "V"],
                                            # 25209: ["Control current", 0.1, "A"],
                                            # 25210: ["Inverter current", 0.1, "A"],
                                            # 25211: ["Grid current", 0.1, "A"],
                                            # 25212: ["Load current", 0.1, "A"],
        self.iPInverter = i[13]             # 25213: ["Inverter power(P)", 1, "W"],
        self.iPGrid = i[14]                 # 25214: ["Grid power(P)", 1, "W"],
        self.iPLoad = i[15]                 # 25215: ["Load power(P)", 1, "W"],
        self.iLoadPercent = i[16]           # 25216: ["Load percent", 1, "%"],
        self.iSInverter = i[17]             # 25217: ["Inverter complex power(S)", 1, "VA"],
        self.iSGrid = i[18]                 # 25218: ["Grid complex power(S)", 1, "VA"],
        self.iSLoad = i[19]                 # 25219: ["Load complex power(S)", 1, "VA"],
                                            # 25221: ["Inverter reactive power(Q)", 1, "var"],
                                            # 25222: ["Grid reactive power(Q)", 1, "var"],
                                            # 25223: ["Load reactive power(Q)", 1, "var"],
                                            # 25225: ["Inverter frequency", 0.01, "Hz"],
                                            # 25226: ["Grid frequency", 0.01, "Hz"],       
        self.iRadiatorTemperature = i[33]   # 25233: ["AC radiator temperature", 1, "°C"],
                                            # 25234: ["Transformer temperature", 1, "°C"],
                                            # 25235: ["DC radiator temperature", 1, "°C"],
                                            # 25237: ["Inverter relay state", 1, ""],
                                            # 25238: ["Grid relay state", 1, ""],
                                            # 25239: ["Load relay state", 1, ""],
                                            # 25240: ["N_Line relay state", 1, ""],
                                            # 25241: ["DC relay state", 1, ""],
                                            # 25242: ["Earth relay state", 1, ""],
                                            # 25245: ["Accumulated charger power high", 1000, "kWh"],
                                            # 25246: ["Accumulated charger power low", 0.1, "kWh"],
        self.iAccumulatedDischargerPower = (i[47] * 1000) + (i[48] / 10.0) # 25247: ["Accumulated discharger power high", 1000, "kWh"],
                                            # 25248: ["Accumulated discharger power low", 0.1, "kWh"],
                                            # 25249: ["Accumulated buy power high", 1, "kWh"],
                                            # 25250: ["Accumulated buy power low", 0.1, "kWh"],
                                            # 25251: ["Accumulated sell power high", 1, "kWh"],
                                            # 25252: ["Accumulated sell power low", 0.1, "kWh"],
        self.iAccumulatedLoadPower = (i[53] * 1000) + (i[54] / 10.0)  # 25253: ["Accumulated load power high", 1, "kWh"],
                                            # 25254: ["Accumulated load power low", 0.1, "kWh"],
        self.iAccumulatedSelfusePower = (i[55] * 1000) + (i[56] / 10.0 )    # 25255: ["Accumulated self_use power high", 1000, "kWh"],
                                            # 25256: ["Accumulated self_use power low", 0.1, "kWh"],
                                            # 25257: ["Accumulated PV_sell power high", 1, "kWh"],
                                            # 25258: ["Accumulated PV_sell power low", 0.1, "kWh"],
                                            # 25259: ["Accumulated grid_charger power high", 1, "kWh"],
                                            # 25260: ["Accumulated grid_charger power low", 0.1, "kWh"],
        self.iError = bitmaskText(False, i[61], iError1s)               # 25261	Error message 1
        self.iError += bitmaskText(self.iError != "", i[62], iError2s)  # 25262	Error message 2
        self.iError += bitmaskText(self.iError != "", i[63], iError3s)  # 25263	Error message 3
        self.iWarning = bitmaskText(False, i[65], iWarning1s)           # 25265	Warning message 1
        self.iWarning += bitmaskText(self.iWarning != "", i[66], iWarning2s) # 25266	Warning message 2
                                            # 25271: ["Hardware version", 1, ""],
                                            # 25272: ["Software version", 1, ""],
        self.iBattPower = bitmaskNegative(i[73])    # 25273: ["Battery power", 1, "W"],
        self.iBattCurrent = bitmaskNegative(i[74])  # 25274: ["Battery current", 1, "A"],
        return i
  
    def setSBU(self): # Solar Battery Utility
        self.writeRegister(20109, 1)  # 20109	RW	Energy use mode	"48V:1:SBU;2:SUB;3:UTI;4:SOL (for PV;PH) |  1:BAU; 3:UTI;4:BOU (for EP) | 12V 24V:1:SBU;;3:UTI;4:SOL (for PV;PH) | 1:BU; 3:UTI (for EP)
        return super().setSBU()

    def setSUB(self): # todo: Solar Utility Battery
        raise NotImplementedError("SUB is not available for this inverter") # there shall be compatiblity check since likely 48v inverter may have this function
        return super().setSUB()

    def setUtility(self): # Utility first
        self.writeRegister(20109, 3) # 20109	RW	Energy use mode	"48V:1:SBU;2:SUB;3:UTI;4:SOL (for PV;PH) |  1:BAU; 3:UTI;4:BOU (for EP) | 12V 24V:1:SBU;;3:UTI;4:SOL (for PV;PH) | 1:BU; 3:UTI (for EP)
        return super().setUtility()

'''# unit test section
def utRead(register: int): # ask for inverter response from console
    r = input(f"Enter message for {register}: ").encode('utf-8')
    return r
'''
# Example usage
if __name__ == "__main__": # testing and debugging
    utMessages = {
        20100: [0,1,2200,5000,0,1,1,1,0,
                1, # 20109	RW	Energy use mode	"48V:1:SBU;2:SUB;3:UTI;4:SOL (for PV;PH) |  1:BAU; 3:UTI;4:BOU (for EP) | 12V 24V:1:SBU;;3:UTI;4:SOL (for PV;PH) | 1:BU; 3:UTI (for EP)
                0,0,1,44,44,0,0,130,
                132, # 20118	RW	Battery stop discharging voltage	0.1V  
                136, # 20119	RW	Battery stop charging voltage	0.1V
                0,125,134,138,12,200,200,120,150,1,200,125,700,0,0,0,0,0,0,0,0,0,43,2,1], # 45 values expected
        15200: [0,3, # WorkStates = { 0: "Initialization", 1: "Selftest", 2: "Work", 3: "Stop" }
                0, # mpptStates = { 0: "S", 1: "MPPT", 2: "CL" }
                0, # chargingStates = { 0: "S", 1: "A", 2: "F", 3: "EQ" } 
                0,
                139, # pvVoltage .1V
                132, # BatteryVoltage .1V
                0, # charger current
                0, # charger power
                27, # pvRadiatorTemperature
                0,0,0,
                32, # pvError bitmask
                0, # pvWarning bitmask
                12,600,
                0,152, # pvAccumulatedPower 15217 mWh, 15218 .1 KWh
                0,0,0], # 22 values expected
        25200: [0,6, # WorkStates = { 0: "Power On", 1: "Self Test", 2: "Off Grid", 3: "Grid-Tie", 4: "ByPass", 5: "Stop", 6: "Grid charging" }
                230,1000,0,
                134, # 25205: ["Battery voltage", 0.1, "V"],
                0, # 25206: ["Inverter voltage", 0.1, "V"],
                2227, # 25207: ["Grid voltage", 0.1, "V"],
                4565,0,0,12,12,
                0, # 25213: ["Inverter power(P)", 1, "W"],
                224, # 25214: ["Grid power(P)", 1, "W"],
                224, # 25215: ["Load power(P)", 1, "W"],
                24, # 25216: ["Load percent", 1, "%"],
                0,263,257,0,0,136,132,0,4996,4996,0,0,0,0,0,0,
                35, # 25233: ["AC radiator temperature", 1, "°C"],
                0,32,0,1,1,1,0,1,0,0,0,0,0,
                0,182, # 25247: ["Accumulated discharger power high", 1000, "kWh"], 25248: ["low", 0.1, "kWh"],
                0,0,0,0,
                0,6024, # 25253: ["Accumulated load power high", 1, "kWh"], 25254: ["low", 0.1, "kWh"],
                0,182,0,0,
                0,0,0, # 25261	Error message 1, 25262	Error message 2, 25263	Error message 3
                0,
                0,0, # 25265	Warning message 1, 25266	Warning message 2
                0,0,0,0,65535,65535,
                10101, # 25273: ["Battery power", 1, "W"], bitmasked
                22535, # 25274: ["Battery current", 1, "A"], bitmasked
                0,0] # 75 values expected
    }

    i: UPSoffgrid = GreenCell(True, "SIMULATOR")
    print(i.jSON("GreenCell"))
    i.setBestEnergyUse(50.5, 44)