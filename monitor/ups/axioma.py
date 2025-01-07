import cmd
import time
from typing import Self
from ups import UPSserial
import re

def extract_values(input_string):
    # Define the regular expression pattern to match numeric values (including decimal points)
    pattern = r"\d+\.\d+|\d+"
    
    # Find all matches in the input string
    matches = re.findall(pattern, input_string)
    
    return matches

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

class Axioma(UPSserial):

    def readSerialCRC(self, cmd: str):
        pass

    def resetSerial(self):
        if hasattr(super, 'scc'):
            super.scc.reset_input_buffer()
            super.scc.reset_output_buffer()

    def reopenSerial(self):
        if hasattr(super, 'scc'):
            super.scc.close()
            time.sleep(1)
            super.scc.open()

    def readSerial(self, cmd: str, nakPossible: bool, breakOnEmpty: bool = False):
        if hasattr(super, 'scc'):
            self.resetSerial()
            super.scc.write(bytes.fromhex(cmd))
            super.scc.flush()
            r = super.scc.readline()
            self.resetSerial()            
        else:
            r = input("Enter message for {cmd}: ")
                    
        if (r == b'' or r == '') and not breakOnEmpty: # connection broken, reopen and re-read one more time
            self.reopenSerial()
            return self.readSerial(cmd, nakPossible, True)

        if (r == b'(NAKss\r' or r == '(NAKss') and not nakPossible: # if NAK received, try again just once to break recursion
            time.sleep(0.4)
            return self.readSerial(cmd, True)
        
        if self.isDebug:
            print("for {cmd} response {r}")
        return r

    def batCurrent(self, charge: float, discharge: float):
        if discharge > 0.0:
            return discharge
        else:
            return -charge
    
    def __init__(self, isDebug: bool, device_path: str):
        super().__init__(isDebug, device_path, 2400)
        self.readQPIGS()

    def readQPIRI(self): # Device Rating Information inquiry
        r = self.readSerial("5150495249F8540D") # "QPIRI")
        v = extract_values(r)        
        """
        BBB.B Grid rating voltage B is an integer ranging from 0 to 9. The units is V.
C CC.C Grid rating current C is an Integer ranging from 0 to 9. The units is A. 
D DDD.D AC output rating voltage D is an Integer ranging from 0 to 9. The units is V.
E EE.E AC output rating frequency E is an Integer ranging from 0 to 9. The units is Hz.
F FF.F AC output rating current F is an Integer ranging from 0 to 9. The unit is A.
H HHHH AC output rating apparent power H is an Integer ranging from 0 to 9. The unit is VA.
I IIII AC output rating active power I is an Integer ranging from 0 to 9. The unit is W.
J JJ.J Battery rating voltage J is an Integer ranging from 0 to 9. The units is V.
K KK.K Battery re-charge voltage K is an Integer ranging from 0 to 9. The units is V.
l JJ.J Battery under voltage J is an Integer ranging from 0 to 9. The units is V.
M KK.K Battery bulk voltage K is an Integer ranging from 0 to 9. The units is V
LL.L Battery float voltage L is an Integer ranging from 0 to 9. The units is V.
O O Battery type 0: AGM 1: Flooded 2: User 3: Pylon 5: Weco 6: Soltaro 8: Lib 9: Lic
P PP Max AC charging current P is an Integer ranging from 0 to 9 The units is A.
If the max AC charging current is greater than 99A, then return to PPP
Q QQ0 Max charging current Q is an Integer ranging from 0 to 9. The units is A.
O O Input voltage range 0: Appliance 1: UPS
P P Output source priority 0: UtilitySolarBat 1: SolarUtilityBat 2: SolarBatUtility
Q Q Charger source priority 1: Solar first 2: Solar + Utility 3: Only solar charging permitted
R R Parallel max num R is an Integer ranging from 0 to 9. 
S SS Machine type 00: Grid tie; 01: Off Grid; 10: Hybrid.
T T Topology 0: transformerless 1: transformer
U U Output mode 00: single machine output 01: parallel output 02: Phase 1 of 3 Phase output 03: Phase 2 of 3 Phase output 04: Phase 3 of 3 Phase output 05: Phase 1 of 2 Phase output 06: Phase 2 of 2 Phase output (120°) 07: Phase 2 of 2 Phase output (180°)
V VV.V Battery re-discharge voltage V is an Integer ranging from 0 to 9. The unit is V.
W W PV OK condition for parallel 0: As long as one unit of inverters has connect PV, parallel system willconsider PV OK; 1: Only All of inverters have connect PV, parallel system will consider PV OK
X X PV power balance 0: PV input max current will be the max charged current; 1: PV input max power will be the sum of the max charged power and loads power.
Y YYY Max. charging time at C.V stage (only 48V model)
Y is an Integer ranging from 0 to 9. The unit is minute.
Z Z Operation Logic (only 48V model) 0: Automatically 1: On-line mode 2: ECO mode
A1 CCC Max discharging current (only 48V model) C is an integer ranging from 0 to 9. The units is A.

        """
        pass

    def readQPIGS(self): # Device general status parameters inquiry
        r = self.readSerial("5150494753B7A90D", False) # "QPIGS")
        v = extract_values(r)        
        if len(v) > 1:
            self.iGridVoltage = float(v[0]) # BBB.B Grid voltage B is an Integer number 0 to 9. The units is V
                                            # CC.C Grid frequency C s an Integer number 0 to 9. The units is Hz.
        if len(v) > 2:
            self.iVoltage = float(v[2])     # DDD.D AC output voltage D is an Integer number 0 to 9. The units is V.
                                            # EE.E AC output frequency E is an Integer number from 0 to 9. The units is Hz.
        if len(v) > 4:
            self.iPLoad = int(v[4])         # FFFF AC output apparent power F is an Integer number from 0 to 9. The units is V
        if len(v) > 5:
            self.iSLoad = int(v[5])         # GGGG AC output active powerG is an Integer ranging from 0 to 9. The units is W
        if len(v) > 6:
            self.iLoadPercent = int(v[6])   # HHH Output load percent DEVICE: HHH is Maximum of W% or VA%. VA% is a percent of apparent power. W% is a percent of active power. The units is %.
                                            # III BUS voltage I is an Integer ranging from 0 to 9. The units is V.
        if len(v) > 8:
            self.iBatteryVoltage = float(v[8]) # JJ.JJ Battery voltage J is an Integer ranging from 0 to 9. The units is V.
        if len(v) > 15:
            self.iBattCurrent = self.batCurrent(float(v[9]), float(v[15]))  # KKK Battery charging current K is an Integer ranging from 0 to 9. The units is A.
                                            # OOO Battery capacity X is an Integer ranging from 0 to 9. The units is %.
            self.pvRadiatorTemperature = iRadiatorTemperature = int(v[11]) # TTTT Inverter heat sink temperature T is an integer ranging from 0 to 9. The units is ℃（NTC A/D value for Axpert 1~3K）
            self.pvChargerCurrent = float(v[12])        # EE.E PV1 Input current E is an Integer ranging from 0 to 9. The units is A.
            self.pvVoltage = float(v[13])               # UUU.U PV1 Input voltage U is an Integer ranging from 0 to 9. The units is V.
            self.pvBatteryVoltage = float(v[14])        # WW.WW Battery voltage from SCCW is an Integer ranging from 0 to 9. The units is V.
#            self.iBattCurrent = int(v[15]) # PPPPP Battery discharge current P is an Integer ranging from 0 to 9. The units is A.
                                            # b7b6b5b4b3b2b1b0  Device status b7: add SBU priority version, 1: yes,0: no
                                            # b6: configuration status: 1: Change 0: unchanged
                                            # b5: SCC firmware version 1: Updated 0: unchanged
                                            # b4: Load status: 0: Load off 1:Load on
                                            # b3: battery voltage to steady while charging
                                            # b2: Charging status
                                            # b1: Charging status(SCC charging on/off)
                                            # b0: Charging status(AC charging on/off)
                                            # b2b1b0: 000: Do nothing 110: Charging on with SCC charge on 101: Charging on with AC charge on 111: Charging on with SCC and AC charge on
                                            # QQ Battery voltage offset for fans on Q is an Integer ranging from 0 to 9. The unit is 10mV.
                                            # VV EEPROM version V is an Integer ranging from 0 to 9. 
        if len(v) > 19:
            self.pvChargerPower = int(v[19])     # MMMMM PV1 Charging power M is an Integer ranging from 0 to 9. The unit is watt.
                                        # b10b9b8 Device status b10: flag for charging to floating mode b9: Switch On b8: flag for dustproof installed(1-dustproof installed,0-no dustproof, only available for Axpert V series)
                                        # Y Solar feed to grid status (reserved feature) 0: normal 1: solar feed to grid
                                        # ZZ Set country customized regulation (reserved feature) 00: India 01: Germany 02: South America
                                        # AAAA Solar feed to grid power (reserved feature) A is an Integer ranging from 0 to 9. The units is W. # Device general status parameters inquiry
        self.iBattPower = self.iBattCurrent * self.iBatteryVoltage

    def readQMOD(self): # Device Mode inquiry
        r = self.readSerialCRC("QMOD")
    """
    QMOD<cr>: Device Mode inquiry
Computer: QMOD<CRC><cr>
Device: (M<CRC><cr>
MODE CODE(M) Notes
P Power on mode
S Standby mode
L Line mode
B Battery mode
F Fault mode
D Shutdown mode
    """
    def readQPIWS(self): # Device Warning Status inquiry
        pass
    def readQDI(self): # The default setting value information
        pass
    def readQET(self): # Query total PV generated energy
        pass
    def readQLT(self): #  Query total output load energy
        pass

    """
       icEnergyUse = icEnergyUses[ic[9]]        # 20109	RW	Energy use mode	"48V:1:SBU;2:SUB;3:UTI;4:SOL (for PV;PH) |  1:BAU; 3:UTI;4:BOU (for EP) | 12V 24V:1:SBU;;3:UTI;4:SOL (for PV;PH) | 1:BU; 3:UTI (for EP)
      icBatteryStopDischarging = ic[18] / 10.0 # 20118	RW	Battery stop discharging voltage	0.1V  
      icBatteryStopCharging = ic[19] / 10.0    # 20119	RW	Battery stop charging voltage	0.1V  

      if pv[1]==2: # work mode
          pvWorkState = mpptStates[pv[2]] + "-" + chargingStates[pv[3]]   # 15201 15202 15203
      else:
          pvWorkState = pvWorkStates[pv[1]]                               # 15201 15202 15203
      pvBatteryRelay = relayStates[pv[11]]                   # 15211
      pvRelay = relayStates[pv[12]]                          # 15212
      pvError = bitmaskText(False, pv[13], pvErrors)         # 15213
      pvWarning = bitmaskText(False, pv[14], pvWarnings)     # 15214
      pvAccumulatedPower = (pv[17] * 1000) + (pv[18] / 10.0) # 15217 mWh, 15218  .1KWh
          
      iWorkState = inverterWorkStates[soc[1]]         # 25201
      iPInverter = soc[13]	                          # 25213: ["Inverter power(P)", 1, "W"],
      iPGrid = soc[14]                                # 25214: ["Grid power(P)", 1, "W"],
      iPLoad = soc[15]                                # 25215: ["Load power(P)", 1, "W"],
      iSInverter = soc[17]                            # 25217: ["Inverter complex power(S)", 1, "VA"],
      iSGrid = soc[18]                                # 25218: ["Grid complex power(S)", 1, "VA"],
      iRelayState = relayStates[soc[37]]              # 25237: ["Inverter relay state", 1, ""],
      iGridRelayState = relayStates[soc[38]]          # 25238: ["Grid relay state", 1, ""],
      iLoadRelayState = relayStates[soc[39]]          # 25239: ["Load relay state", 1, ""],
      iAccumulatedDischargerPower = (soc[47] * 1000) + (soc[48] / 10.0) # 25247: ["Accumulated discharger power high", 1000, "kWh"],
      iAccumulatedLoadPower = (soc[53] * 1000) + (soc[54] / 10.0)  # 25253: ["Accumulated load power high", 1, "kWh"],
                                                      # 25254: ["Accumulated load power low", 0.1, "kWh"],
      iAccumulatedSelfusePower = (soc[55] * 1000) + (soc[56] / 10.0 )    # 25255: ["Accumulated self_use power high", 1000, "kWh"],
                                                      # 25256: ["Accumulated self_use power low", 0.1, "kWh"],
      iError = bitmaskText(False, soc[61], iError1s)            # 25261	Error message 1
      iError += bitmaskText(iError != "", soc[62], iError2s)    # 25262	Error message 2
      iError += bitmaskText(iError != "", soc[63], iError3s)    # 25263	Error message 3
      iWarning = bitmaskText(False, soc[65], iWarning1s)           # 25265	Warning message 1
      iWarning += bitmaskText(iWarning != "", soc[66], iWarning2s) # 25266	Warning message 2

    """  
    def setSBU(self):
        return super.setSBU()

    def setSUB(self):
        return super.setSUB()

    def setUtility(self):
        return super.setUtility()

# Example usage
if __name__ == "__main__":

    r = "(222.2 49.9 222.2 49.9 0199 0157 006 460 27.00 000 100 0039 00.0 151.1 00.00 00000 01010110 00 01 00000 110 0 01 0000)Ó"
    v = extract_values(r)        
    print(v)