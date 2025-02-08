import cmd
import time
import re
import crcmod
from datetime import datetime
if __name__ == "__main__":
    from __init__ import UPSserial, UPShybrid, addText
else:
    from . import UPSserial, UPShybrid, addText

# constants: inverter communication commands
cmdRetryCount = 3
cmdQPI = "515049beac0d"         # QPI
cmdQPIGS = "5150494753b7a90d"   # QPIGS
cmdQPIRI = "5150495249f8540d"   # QPIRI
cmdQMOD = "514d4f4449c10d"      # QMOD
cmdQPIWS = "5150495753b4da0d"   # QPIWS
cmdQ1 = "51311bfc0d"            # Q1
cmdSBU = "504f503032e20b0d"     # POP02
cmdSUB = "504f503031d2690d"     # POP01
cmdUtility = "504f503030c2480d" # POP00

compatibleProtocols = ['(PI30']

def extract_values(input_string): # extracting values from response into array
    # Define the regular expression pattern to match numeric values (including decimal points)
    pattern = r"\d+\.\d+|\d+"
    
    # Find all matches in the input string
    matches = re.findall(pattern, input_string)
    
    return matches

def axiomaCustomCRC(): # custom CRC function for Axioma inverter
    polynomial = 0x11021
    initial_value = 0x0000
    final_xor = 0x0000
    reflect = False

    crc_func = crcmod.mkCrcFun(polynomial, initCrc=initial_value, xorOut=final_xor, rev=reflect)
    return crc_func

def incrementSpecialChar(crc): # apecial characters are being replaced
    # Define the set of special characters to check against
    specialChars = {0x28, 0x0d, 0x0a}

    # Extract the high and low bytes
    hb = (crc >> 8) & 0xFF
    lb = crc & 0xFF

    # Increment bytes if they are special ones
    hb = (hb + 1) & 0xFF if hb in specialChars else hb
    lb = (lb + 1) & 0xFF if lb in specialChars else lb

    # Combine the high and low bytes back into a two-byte value
    return (hb << 8) | lb

def axiomaCRC(data): # CRC function for Axioma inverter
    crc_func = axiomaCustomCRC()
    crc_value = incrementSpecialChar(crc_func(data))
    return crc_value.to_bytes(2, byteorder='big')

class Axioma(UPSserial, UPShybrid): # object to communicate with and manage Axioma inverter
        
    def readSerial(self, cmd: str, retryCount: int, breakOnEmpty: bool = False): # read data with CRC check
        
        if retryCount <= 0:
            raise IOError(f"Error reading RS232 port {cmd}")

        if hasattr(self, 'scc'): # check if we are live in production or unit testing
            time.sleep(0.5)
            r = super().readSerial(cmd)
        else:
            if cmd.lower() in utMessages:
                r = utMessages[cmd.lower()]
            else:
                r = utRead(cmd)

        #if self.isDebug: 
        print(f"{datetime.now()}\t{cmd}\t{r}") # format usable for putting into Excel (hopefully)
        
        if len(r) < 3 and not breakOnEmpty: # connection broken, reopen and re-read one more time
            self.reopenSerial()
            return self.readSerial(cmd, retryCount - 1, True)
        
        # check CRC and re-read if not match
        crc = axiomaCRC(r[:-3])
        if r[-3:][:2] != crc: # CRC do not match, reset and re-read
            print(f"Bad CRC {r[-3:][:2]} != {crc}")
            time.sleep(0.4)
            self.reopenSerial()
            return self.readSerial(cmd, retryCount - 1)

        if r[:-3] == b'(NAK' : # if NAK received unexpectedly, try again just once to not recurse
            time.sleep(0.4)
            return self.readSerial(cmd, retryCount - 1)
        
        return r[:-3].decode('utf-8', errors='ignore')

    def setSerial(self, cmd: str): # send command to change values within inverter
        return self.readSerial(cmd, cmdRetryCount) == '(ACK'

    def batCurrent(self, charge: float, discharge: float): # merge battery current into one variable instead of two
        return discharge if discharge > 0.0 else -charge
    
    def __init__(self, isDebug: bool, device_path: str):
        super().__init__(isDebug, device_path, 2400)
        
        if not self.readQPI() in compatibleProtocols:
            raise TypeError("Incompatible inverter protocol")

        self.readQPIGS()
        self.readQPIRI()
        self.readQMOD()
        self.readQPIWS()
        self.readQ1()
        
    def readQPI(self): # Device Protocol validation
        r = self.readSerial(cmdQPI, cmdRetryCount) # "QPI")
        return r
    
    def readQPIRI(self): # Device Rating Information inquiry
        icEnergyUses = { 0: "Uti", 1: "SUB", 2: "SBU" }

        r = self.readSerial(cmdQPIRI, cmdRetryCount) # "QPIRI")
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

    def readQPIGS(self): # Device general status parameters inquiry
        
        pvWorkStates = { '000': "Off", '100': "?c", '110': "Sc", '101': "Gc", '111': "SGc" }
    
        r = self.readSerial(cmdQPIGS, cmdRetryCount) # "QPIGS")
        v = extract_values(r)        
        if len(v) > 1:
            self.iGridVoltage = float(v[0]) # BBB.B Grid voltage B is an Integer number 0 to 9. The units is V
                                            # CC.C Grid frequency C s an Integer number 0 to 9. The units is Hz.
        if len(v) > 2:
            self.iVoltage = float(v[2])     # DDD.D AC output voltage D is an Integer number 0 to 9. The units is V.
                                            # EE.E AC output frequency E is an Integer number from 0 to 9. The units is Hz.
        if len(v) > 4:
            self.iSLoad = int(v[4])         # FFFF AC output apparent power F is an Integer number from 0 to 9. The units is VA
        if len(v) > 5:
            self.iPLoad = int(v[5])         # GGGG AC output active power G is an Integer ranging from 0 to 9. The units is W
        if len(v) > 6:
            self.iLoadPercent = int(v[6])   # HHH Output load percent DEVICE: HHH is Maximum of W% or VA%. VA% is a percent of apparent power. W% is a percent of active power. The units is %.
                                            # III BUS voltage I is an Integer ranging from 0 to 9. The units is V.
        if len(v) > 8:
            self.iBatteryVoltage = float(v[8]) # JJ.JJ Battery voltage J is an Integer ranging from 0 to 9. The units is V.
        if len(v) > 15:
            self.iBattCurrent = self.batCurrent(float(v[9]), float(v[15]))  # KKK Battery charging current K is an Integer ranging from 0 to 9. The units is A.
                                            # OOO Battery capacity X is an Integer ranging from 0 to 9. The units is %.
            self.pvRadiatorTemperature = self.iRadiatorTemperature = int(v[11]) # TTTT Inverter heat sink temperature T is an integer ranging from 0 to 9. The units is ℃（NTC A/D value for Axpert 1~3K）
            self.pvChargerCurrent = float(v[12])    # EE.E PV1 Input current E is an Integer ranging from 0 to 9. The units is A.
            self.pvVoltage = float(v[13])           # UUU.U PV1 Input voltage U is an Integer ranging from 0 to 9. The units is V.
            self.pvBatteryVoltage = float(v[14])    # WW.WW Battery voltage from SCCW is an Integer ranging from 0 to 9. The units is V.
            # self.iBattCurrent = int(v[15])        # PPPPP Battery discharge current P is an Integer ranging from 0 to 9. The units is A.
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
                                            # AAAA Solar feed to grid power (reserved feature) A is an Integer ranging from 0 to 9. The units is W. 
                                            # Device general status parameters inquiry
        self.iBattPower = self.iBattCurrent * self.iBatteryVoltage
        self.iPInverter = int(self.pvChargerPower + self.iBattPower)
        if len(v) > 23:
            self.pvReturnGrid = int(v[23])
        # todo: there shall be more sophisticated formula accounting VA and VAr
        self.iPGrid = int(self.iPLoad - (self.iPInverter * .95) + 65 - self.pvReturnGrid) # include self consumption approximate, efficiency and exclude return to grid power
        self.iSGrid = int(self.iSLoad * self.iPGrid / self.iPLoad) # hopefully it is proportional
        if self.iPInverter < 0:
            self.iPInverter = 0 # it happens when battery is charged from grid
        #if self.iPGrid < 0:
        #    self.iPGrid = 0
        return v

    def readQMOD(self): # Device Mode inquiry
        r = self.readSerial(cmdQMOD, cmdRetryCount) # "QMOD")
        if len(r) > 1:
            iWorkStates = { 'P': "Power on", 'S': "Standby", 'L': "Line", 'B': "Battery", 'F': "Fault", 'D': "Shutdown" }
            s = r[1]
            self.iWorkState = iWorkStates[s] if s in iWorkStates else s
        # QMOD<cr>: Device Mode inquiry
        # Computer: QMOD<CRC><cr>
        # Device: (M<CRC><cr>
        # MODE CODE(M) Notes
        return r

    def readQPIWS(self): # Device Warning Status inquiry (100000000000000000000000000000000000
        bitOK = "0"
        r = self.readSerial(cmdQPIWS, cmdRetryCount)[1:]

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

        for index, attr, message, *optional in messages: # converting bitmask to text
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
        # pvAccumulatedPower
        pass
    def readQLT(self): # todo: Query total output load energy - NAK
        # iAccumulatedLoadPower
        pass

    def readQ1(self): # undocumented temperature data
        
        r = self.readSerial(cmdQ1, cmdRetryCount) # "QPIGS")
        v = extract_values(r)        
        if len(v) > 4:
            self.tRadiatorTemperature = int(v[4])
        if len(v) > 5:
            self.bRadiatorTemperature = int(v[5])
        if len(v) > 6:
            self.iRadiatorTemperature = int(v[6])
        if len(v) > 7:
            self.pvRadiatorTemperature = int(v[7])

    """
      iSInverter = soc[17]                            # 25217: ["Inverter complex power(S)", 1, "VA"],
      iSGrid = soc[18]                                # 25218: ["Grid complex power(S)", 1, "VA"],
      iAccumulatedDischargerPower = (soc[47] * 1000) + (soc[48] / 10.0) # 25247: ["Accumulated discharger power high", 1000, "kWh"],
      iAccumulatedSelfusePower = (soc[55] * 1000) + (soc[56] / 10.0 )    # 25255: ["Accumulated self_use power high", 1000, "kWh"], # 25256: ["Accumulated self_use power low", 0.1, "kWh"],
    """  
    def setOutputSource(self, mode: str, cmd: str): # change inverter output source mode
        r = self.setSerial(cmd)
        print(f"{mode} {cmd} set {'OK' if r else 'Fail'}")
        return r
    """
    POP<NN><cr>: Setting device output source priority
    Computer: POP<NN><CRC><cr>
    Device: (ACK<CRC><cr> if device accepts this command, otherwise, responds (NAK<CRC><cr>
    Set output source priority, 00 for UtilitySolarBat, 01 for SolarUtilityBat, 02 for SolarBatUtility
    """
    def setSBU(self): # Solar Battery Utility POP02 504f503032e20a0d -> 0x504f503032e20b0d
        return super().setSBU() and self.setOutputSource("SBU", cmdSBU)

    def setSUB(self): # Solar Utility Battery POP01 504f503031d2690d
        return super().setSUB() and self.setOutputSource("SUB", cmdSUB)

    def setUtility(self): # Utility first POP00 504f503030c2480d
        return super().setUtility() and self.setOutputSource("Utility", cmdUtility)

# unit test section
def utRead(cmd: str): # ask for inverter response from console
    r = input(f"Enter message for {bytes.fromhex(cmd[:-6]).decode('utf-8')}: ").encode('utf-8')
    if r.lower() not in [b'', b'exit']:
        #todo: convert from hex if needed
        r = r + axiomaCRC(r) + b'\r'
    return r

# Example usage
if __name__ == "__main__": # testing and debugging
    utMessages = {
        "515049beac0d": b'(PI30\x9a\x0b\r', # QPI
        "5150494753b7a90d": b'(221.9 49.9 220.7 49.9 0352 0318 012 404 26.20 000 075 0026 02.5 126.7 00.00 00001 00010000 00 01 00328 010 0 01 0000\x19\xe8\r', # QPIGS
        "5150495249f8540d": b'(220.0 13.6 220.0 50.0 13.6 3000 3000 24.0 25.5 23.0 28.2 27.0 2 40 040 1 2 2 1 01 0 0 27.0 0 1\x10\xb6\r', # QPIRI
        "514d4f4449c10d": b'(B\xe7\xc9\r', # QMOD
        "5150495753b4da0d": b'(000000000000000000000000000000000000<\x8e\r', # QPIWS
        "51311bfc0d": b'(01 00 00 000 028 016 016 030 00 00 000 0030 0000 13\x0f\xd5\r' # Q1
    }
    while True:
        i: UPShybrid = Axioma(True, "SIMULATOR")
        print(i.jSON("Axioma"))
        i.setBestEnergyUse(150, 135)
     
        for cmd in utMessages:
            s = utRead(cmd)
            match s.lower():
                case b'':
                    pass
                case b'exit':
                    exit()
                case _:
                    utMessages[cmd] = s

    """
    # QBEQI (0 060 030 040 030 29.20 000 120 0 0000
    # QFLAG (EbzDadjkuvxy]
    # QPIRI (220.0 13.6 220.0 50.0 13.6 3000 3000 24.0 25.5 21.0 28.2 27.0 0 40 040 1 1 2 1 01 0 0 27.0 0 1
    # QVFW (VERFW:00043.19
    # POP01 (ACK9 \r
    """