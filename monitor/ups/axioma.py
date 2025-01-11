import cmd
import time
import re
from typing import Self
from datetime import datetime
if __name__ == "__main__":
    from __init__ import UPSserial, addText
else:
    from . import UPSserial, addText

def extract_values(input_string):
    # Define the regular expression pattern to match numeric values (including decimal points)
    pattern = r"\d+\.\d+|\d+"
    
    # Find all matches in the input string
    matches = re.findall(pattern, input_string)
    
    return matches
"""
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
"""
class Axioma(UPSserial):
        
    def readSerialCRC(self, cmd: str): # todo : make CRC
        pass

    def resetSerial(self):
        if hasattr(self, 'scc'):
            self.scc.reset_input_buffer()
            self.scc.reset_output_buffer()

    def reopenSerial(self):
        if hasattr(self, 'scc'):
            self.scc.close()
            time.sleep(1)
            self.scc.open()

    def readSerial(self, cmd: str, nakPossible: bool, breakOnEmpty: bool = False): # todo: CRC check
        if hasattr(self, 'scc'):
            self.resetSerial()
            self.scc.write(bytes.fromhex(cmd))
            self.scc.flush()
            r = self.scc.readline()
            self.resetSerial()            
        else:
            r = input(f"Enter message for {cmd}: ").encode('utf-8')
            if r != b'':
                r = r + b'\r'

        #if self.isDebug:
        print(f"{datetime.now()} for {cmd} response\t{r}")
                    
        if len(r) < 3 and not breakOnEmpty: # connection broken, reopen and re-read one more time
            self.reopenSerial()
            return self.readSerial(cmd, nakPossible, True)

        if r[:-3] == b'(NAK' and not nakPossible: # if NAK received unexpectedly, try again just once to not recurse
            time.sleep(0.4)
            return self.readSerial(cmd, True)
        
        # todo: check CRC and re-read if not match

        return r.decode('utf-8', errors='ignore')

    def setSerial(self, cmd: str):
        return self.readSerial(cmd, True)[:-3] == '(ACK'

    def batCurrent(self, charge: float, discharge: float):
        return discharge if discharge > 0.0 else -charge
    
    def __init__(self, isDebug: bool, device_path: str):
        super().__init__(isDebug, device_path, 2400)
        
        if not self.readQPI():
            raise TypeError("Incompatible inverter protocol")

        self.readQPIGS()
        time.sleep(0.5)
        self.readQPIRI()
        time.sleep(0.5)
        self.readQMOD()
        time.sleep(0.5)
        self.readQPIWS()
        
    def readQPI(self): # Device Protocol validation
        r = self.readSerial("515049beac0d", False) # "QPI")
        return len(r) == 8 and r[:-3] == b'(PI30'
    
    def readQPIRI(self): # todo: Device Rating Information inquiry
        icEnergyUses = { 0: "Uti", 1: "SUB", 2: "SBU" }

        r = self.readSerial("5150495249F8540D", False) # "QPIRI")
        v = extract_values(r)        
        """
        # BBB.B Grid rating voltage B is an integer ranging from 0 to 9. The units is V.
        # C CC.C Grid rating current C is an Integer ranging from 0 to 9. The units is A. 
        # D DDD.D AC output rating voltage D is an Integer ranging from 0 to 9. The units is V.
        # E EE.E AC output rating frequency E is an Integer ranging from 0 to 9. The units is Hz.
        # F FF.F AC output rating current F is an Integer ranging from 0 to 9. The unit is A.
        # H HHHH AC output rating apparent power H is an Integer ranging from 0 to 9. The unit is VA.
        # I IIII AC output rating active power I is an Integer ranging from 0 to 9. The unit is W.
        # J JJ.J Battery rating voltage J is an Integer ranging from 0 to 9. The units is V.
        """
        if len(v) > 9:
            self.icBatteryStopDischarging = float(v[8])        # K KK.K Battery re-charge voltage K is an Integer ranging from 0 to 9. The units is V.
        """
        # l JJ.J Battery under voltage J is an Integer ranging from 0 to 9. The units is V.
        # M KK.K Battery bulk voltage K is an Integer ranging from 0 to 9. The units is V
        # LL.L Battery float voltage L is an Integer ranging from 0 to 9. The units is V.
        # O O Battery type 0: AGM 1: Flooded 2: User 3: Pylon 5: Weco 6: Soltaro 8: Lib 9: Lic
        # P PP Max AC charging current P is an Integer ranging from 0 to 9 The units is A. If the max AC charging current is greater than 99A, then return to PPP
        # Q QQ0 Max charging current Q is an Integer ranging from 0 to 9. The units is A.
        # O O Input voltage range 0: Appliance 1: UPS
        """
        if len(v) > 17:
            self.icEnergyUse = icEnergyUses[int(v[16])]        # P P Output source priority 0: UtilitySolarBat 1: SolarUtilityBat 2: SolarBatUtility
        """
        # Q Q Charger source priority 1: Solar first 2: Solar + Utility 3: Only solar charging permitted
        # R R Parallel max num R is an Integer ranging from 0 to 9. 
        # S SS Machine type 00: Grid tie; 01: Off Grid; 10: Hybrid.
        # T T Topology 0: transformerless 1: transformer
        # U U Output mode 00: single machine output 01: parallel output 02: Phase 1 of 3 Phase output 03: Phase 2 of 3 Phase output 04: Phase 3 of 3 Phase output 05: Phase 1 of 2 Phase output 06: Phase 2 of 2 Phase output (120°) 07: Phase 2 of 2 Phase output (180°)
        """
        if len(v) > 23:
            self.icBatteryStopCharging = float(v[22])          # V VV.V Battery re-discharge voltage V is an Integer ranging from 0 to 9. The unit is V.
        """
        # W W PV OK condition for parallel 0: As long as one unit of inverters has connect PV, parallel system willconsider PV OK; 1: Only All of inverters have connect PV, parallel system will consider PV OK
        # X X PV power balance 0: PV input max current will be the max charged current; 1: PV input max power will be the sum of the max charged power and loads power.
        # Y YYY Max. charging time at C.V stage (only 48V model)
        # Y is an Integer ranging from 0 to 9. The unit is minute.
        # Z Z Operation Logic (only 48V model) 0: Automatically 1: On-line mode 2: ECO mode
        # A1 CCC Max discharging current (only 48V model) C is an integer ranging from 0 to 9. The units is A.
        """
        return v

    def readQPIGS(self): # done: Device general status parameters inquiry
        
        pvWorkStates = { '000': "Off", '100': "?c", '110': "Sc", '101': "Gc", '111': "SGc" }
    
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
            self.iSLoad = int(v[5])         # GGGG AC output active power G is an Integer ranging from 0 to 9. The units is W
        if len(v) > 6:
            self.iLoadPercent = int(v[6])   # HHH Output load percent DEVICE: HHH is Maximum of W% or VA%. VA% is a percent of apparent power. W% is a percent of active power. The units is %.
                                            # III BUS voltage I is an Integer ranging from 0 to 9. The units is V.
        if len(v) > 8:
            self.iBatteryVoltage = float(v[8]) # JJ.JJ Battery voltage J is an Integer ranging from 0 to 9. The units is V.
        if len(v) > 15:
            self.iBattCurrent = self.batCurrent(float(v[9]), float(v[15]))  # KKK Battery charging current K is an Integer ranging from 0 to 9. The units is A.
                                            # OOO Battery capacity X is an Integer ranging from 0 to 9. The units is %.
            self.pvRadiatorTemperature = self.iRadiatorTemperature = int(v[11]) # TTTT Inverter heat sink temperature T is an integer ranging from 0 to 9. The units is ℃（NTC A/D value for Axpert 1~3K）
            self.pvChargerCurrent = float(v[12])        # EE.E PV1 Input current E is an Integer ranging from 0 to 9. The units is A.
            self.pvVoltage = float(v[13])               # UUU.U PV1 Input voltage U is an Integer ranging from 0 to 9. The units is V.
            self.pvBatteryVoltage = float(v[14])        # WW.WW Battery voltage from SCCW is an Integer ranging from 0 to 9. The units is V.
            # self.iBattCurrent = int(v[15])            # PPPPP Battery discharge current P is an Integer ranging from 0 to 9. The units is A.
                                            # b7b6b5b4b3b2b1b0  Device status b7: add SBU priority version, 1: yes,0: no
                                            # b6: configuration status: 1: Change 0: unchanged
                                            # b5: SCC firmware version 1: Updated 0: unchanged
                                            # b4: Load status: 0: Load off 1:Load on
                                            # b3: battery voltage to steady while charging
        if len(v) > 16:
            self.pvWorkState = pvWorkStates[v[16][-3:]] # b2: Charging status
                                                        # b1: Charging status(SCC charging on/off)
                                                        # b0: Charging status(AC charging on/off)
                                                        # b2b1b0: 000: Do nothing 110: Charging on with SCC charge on 101: Charging on with AC charge on 111: Charging on with SCC and AC charge on
                                            # QQ Battery voltage offset for fans on Q is an Integer ranging from 0 to 9. The unit is 10mV.
                                            # VV EEPROM version V is an Integer ranging from 0 to 9. 
        if len(v) > 19:
            self.pvChargerPower = int(v[19])     # MMMMM PV1 Charging power M is an Integer ranging from 0 to 9. The unit is watt.
        if len(v) > 20:
            if v[20][0] == '1':                             # b10b9b8 Device status 
                self.pvWorkState = self.pvWorkState + "F"   # b10: flag for charging to floating mode 
            match v[20][1]:                                 # b9: Switch On 
                case '1':
                    self.pvWorkState = self.pvWorkState + "+"   
                case '0':
                    self.pvWorkState = self.pvWorkState + "-"
                                                            # b8: flag for dustproof installed(1-dustproof installed,0-no dustproof, only available for Axpert V series)
                                        # Y Solar feed to grid status (reserved feature) 0: normal 1: solar feed to grid
                                        # ZZ Set country customized regulation (reserved feature) 00: India 01: Germany 02: South America
                                        # AAAA Solar feed to grid power (reserved feature) A is an Integer ranging from 0 to 9. The units is W. # Device general status parameters inquiry
        self.iBattPower = self.iBattCurrent * self.iBatteryVoltage
        self.iPInverter = int(self.pvChargerPower + self.iBattPower)
        self.iPGrid = self.iPLoad - self.iPInverter + 65  # include self consumption approximate
        if self.iPInverter < 0:
            self.iPInverter = 0
        if self.iPGrid < 0:
            self.iPGrid = 0
        return v

    def readQMOD(self): # todo: Device Mode inquiry
        r = self.readSerial("514d4f4449c10d", False) # "QMOD")
        if len(r) > 2:
            iWorkStates = { 'P': "Power on", 'S': "Standby", 'L': "Line", 'B': "Battery", 'F': "Fault", 'D': "Shutdown" }
            s = r[1]
            if s in iWorkStates:
                self.iWorkState = iWorkStates[s]
            else:
                self.iWorkState = s
        # QMOD<cr>: Device Mode inquiry
        # Computer: QMOD<CRC><cr>
        # Device: (M<CRC><cr>
        # MODE CODE(M) Notes
        return r

    def readQPIWS(self): # todo: Device Warning Status inquiry (100000000000000000000000000000000000
        bitOK = "0"
        r = self.readSerial("5150495753b4da0d", False)

        messages = [
            ( 0, "pvWarning", "PV loss"),
            ( 1, "iError", "Inverter fault", "iError"),
            ( 2, "iError", "Bus Over Fault"),
            ( 3, "iError", "Bus Under Fault"),
            ( 4, "iError", "Bus Soft Fail Fault"),
            ( 5, "iWarning", "Line Fail"),
            ( 6, "pvError", "OPVShort Fault"),
            ( 7, "iError", "Inverter voltage too low"),
            ( 8, "iError", "Inverter voltage too high"),
            ( 9, "iError", "Over temperature", "iWarning"),
            (10, "iError", "Fan locked", "iWarning"),
            (11, "iError", "Battery voltage high", "iWarning"),
            (12, "iWarning", "Battery low"),
            (13, "pvWarning", "a13"),
            (14, "iWarning", "Battery under shutdown"),
            (15, "iWarning", "Battery derating"),
            (16, "iError", "Over load", "iWarning"),
            (17, "iWarning", "Eeprom fault"),
            (18, "iError", "Inverter Over Current"),
            (19, "iError", "Inverter Soft Fail"),
            (20, "iError", "Self Test Fail"),
            (21, "pvError", "OP DC Voltage Over"),
            (22, "iError", "Bat Open"),
            (23, "iError", "Current Sensor Fail"),
            (24, "pvWarning", "a24"),
            (25, "pvWarning", "a25"),
            (26, "pvWarning", "a26"),
            (27, "pvWarning", "a27"),
            (28, "pvWarning", "a28"),
            (29, "pvWarning", "a29"),
            (30, "pvWarning", "a30"),
            (31, "iError", "Battery weak"), # (only 48V model) 24V model: a31, a32 is fault code 48V model: a32, a33 is fault code 
            (32, "iError", "a32"),
            (33, "iError", "a33"),
            (34, "pvWarning", "a34"),
            (35, "iWarning", "Battery equalization")
        ]

        fault = len(r) > 1 and r[1] != bitOK

        for index, attr, message, *optional in messages:
            if len(r) > index and r[index] != bitOK:
                if optional and not fault:
                    setattr(self, optional[0], addText(getattr(self, optional[0], ""), message))
                else:
                    setattr(self, attr, addText(getattr(self, attr, ""), message))
        if len(r) < 36:
            self.pvWarning = addText(self.pvWarning, f"Too short error code received {r}")
        pass

    def readQDI(self): # todo: The default setting value information (230.0 50.0 0030 21.0 27.0 28.2 23.0 60 0 0 2 0 0 0 0 0 1 1 1 0 1 0 27.0 0 1)F
        pass
    def readQET(self): # todo: Query total PV generated energy - NAK
        # pvAccumulatedPower = (pv[17] * 1000) + (pv[18] / 10.0) # 15217 mWh, 15218  .1KWh
        pass
    def readQLT(self): # todo: Query total output load energy - NAK
        # iAccumulatedLoadPower = (soc[53] * 1000) + (soc[54] / 10.0)  # 25253: ["Accumulated load power high", 1, "kWh"],              # 25254: ["Accumulated load power low", 0.1, "kWh"],
        pass

    """
      iSInverter = soc[17]                            # 25217: ["Inverter complex power(S)", 1, "VA"],
      iSGrid = soc[18]                                # 25218: ["Grid complex power(S)", 1, "VA"],
      iAccumulatedDischargerPower = (soc[47] * 1000) + (soc[48] / 10.0) # 25247: ["Accumulated discharger power high", 1000, "kWh"],
      iAccumulatedSelfusePower = (soc[55] * 1000) + (soc[56] / 10.0 )    # 25255: ["Accumulated self_use power high", 1000, "kWh"], # 25256: ["Accumulated self_use power low", 0.1, "kWh"],
    """  
    def setOutputSource(self, mode: str, cmd: str):
        r = self.setSerial(cmd)
        print(f"{mode} {cmd} set {'OK' if r else 'Fail'}")
        return r
    """
    POP<NN><cr>: Setting device output source priority
    Computer: POP<NN><CRC><cr>
    Device: (ACK<CRC><cr> if device accepts this command, otherwise, responds (NAK<CRC><cr>
    Set output source priority, 00 for UtilitySolarBat, 01 for SolarUtilityBat, 02 for SolarBatUtility
    """
    def setSBU(self): # POP02 504f503032e20a0d -> 0x504f503032e20b0d
        return super.setSBU() and self.setOutputSource("SBU", "504f503032e20b0d")

    def setSUB(self): # POP01 504f503031d2690d
        return super.setSUB() and self.setOutputSource("SUB", "504f503031d2690d")

    def setUtility(self): # POP00 504f503030c2480d
        return super.setUtility() and self.setOutputSource("Utility", "504f503030c2480d")

# unit test section
def utRead():
    r = input(f"Enter message for {cmd}: ").encode('utf-8')
    if r != b'':
        #todo: convert from hex
        #todo: add CRC   
        r = r + b'\r'
    return r

# Example usage
if __name__ == "__main__":
    utMessages = {
        # QPI b'(PI30\x9a\x0b\r'
        "515049beac0d": b'28504933309a0b0d',
        # QPIGS b'(221.7 50.0 221.7 50.0 0309 0295 010 440 27.00 000 100 0036 00.0 030.1 00.00 00000 00010110 00 01 00000 110 0 01 0000d,\r'
        "5150494753b7a90d": b'283232312e372035302e30203232312e372035302e302030333039203032393520303130203434302032372e3030203030302031303020303033362030302e30203033302e312030302e30302030303030302030303031303131302030302030312030303030302031313020302030312030303030642c0d',
        # QPIRI b'(220.0 13.6 220.0 50.0 13.6 3000 3000 24.0 25.5 21.0 28.2 27.0 0 40 040 1 1 2 1 01 0 0 27.0 0 1\x8d\xd2\r'
        "5150495249f8540d": b'283232302e302031332e36203232302e302035302e302031332e36203330303020333030302032342e302032352e352032312e302032382e322032372e302030203430203034302031203120322031203031203020302032372e30203020318dd20d',
        # QMOD b'(L\x06\x07\r'
        "514d4f4449c10d": b'284c06070d',
        # QPIWS b'(000000000000000000000000000000000000<\x8e\r'
        "5150495753b4da0d": b'283030303030303030303030303030303030303030303030303030303030303030303030303c8e0d'
    }
    while True:
        i = Axioma(True, "SIMULATOR")
        print(i.jSON("Axioma"))

    """
    # QBEQI (0 060 030 040 030 29.20 000 120 0 0000
    # QFLAG (EbzDadjkuvxy]
    # QPIRI (220.0 13.6 220.0 50.0 13.6 3000 3000 24.0 25.5 21.0 28.2 27.0 0 40 040 1 1 2 1 01 0 0 27.0 0 1
    # QVFW (VERFW:00043.19
    # QPI (PI30
    """