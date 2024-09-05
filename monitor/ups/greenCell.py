
from . import Sample, UPS

class GreenCell(UPS):
    def __init__(self, device_path: str):
        super().__init__(device_path, 4, 19200)

    def sample(self) -> Sample:
      
      inverterWorkStates {
        0: "Power On", 
        1: "Self Test", 
        2: "Off Grid", 
        3: "Grid-Tie", 
        4: "ByPass", 
        5: "Stop", 
        6:"Grid charging"
      }
      
      pvWorkStates {
        0: "Initialization mode", 
        1: "Selftest Mode", 
        2: "Work Mode", 
        3: "Stop Mode"
      }
      
      mpptStates {
        0: "Stop", 
        1: "MPPT", 
        2: "Current limiting"
      }
      
      chargingStates {
        0: "Stop", 
        1: "Absorb charge", 
        2: "Float charge", 
        3: "EQ charge"
      }
      
      relayStates {
        0: "Disconnect", 
        1: "Connect"
      }

      pv = self.scc.read_registers(15200, 22)
      print("PV Message: ", pv)
      
      pvWorkState = pvWorkStates[soc[1]]        # 15201
      pvMpptState = mpptStates[soc[2]]          # 15202
      pvChargingState = chargingStates[soc[3]]  # 15203
      pvVoltage = soc[5] / 10.0                 # 15205
      pvBatteryVoltage = soc[6] / 10.0          # 15206
      pvChargerCurrent = soc[7] / 10.0	        # 15207
      pvChargerPower = soc[8]	                  # 15208
      pvRadiatorTemperature = soc[9]            # 15209
      pvBatteryRelay = relayStates[soc[11]]     # 15211
      pvRelay = relayStates[soc[12]]            # 15212
      pvAccumulatedPower = (soc[17] * 1000) + (soc[18] / 10.0) # 15217 mWh, 15218  .1KWh

      soc = self.scc.read_registers(25200, 75)
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
      iAccumulatedLoadPower = (soc[45] * 1000)        # 25245: ["Accumulated charger power high", 1000, "kWh"],
                            + (soc[46] / 10.0)        # 25246: ["Accumulated charger power low", 0.1, "kWh"],
      iAccumulatedDischargerPower = (soc[47] * 1000)  # 25247: ["Accumulated discharger power high", 1000, "kWh"],
                                  + (soc[48] / 10.0)  # 25248: ["Accumulated discharger power low", 0.1, "kWh"],
                                                      # 25249: ["Accumulated buy power high", 1, "kWh"],
                                                      # 25250: ["Accumulated buy power low", 0.1, "kWh"],
                                                      # 25251: ["Accumulated sell power high", 1, "kWh"],
                                                      # 25252: ["Accumulated sell power low", 0.1, "kWh"],
                                                      # 25253: ["Accumulated load power high", 1, "kWh"],
                                                      # 25254: ["Accumulated load power low", 0.1, "kWh"],
      iAccumulatedSelfusePower = (soc[55] * 1000)     # 25255: ["Accumulated self_use power high", 1000, "kWh"],
                               + (soc[56] / 10.0 )    # 25256: ["Accumulated self_use power low", 0.1, "kWh"],
                                                      # 25257: ["Accumulated PV_sell power high", 1, "kWh"],
                                                      # 25258: ["Accumulated PV_sell power low", 0.1, "kWh"],
                                                      # 25259: ["Accumulated grid_charger power high", 1, "kWh"],
                                                      # 25260: ["Accumulated grid_charger power low", 0.1, "kWh"],
                                                      # 25271: ["Hardware version", 1, ""],
                                                      # 25272: ["Software version", 1, ""],
      iBattPower = soc[73]                            # 25273: ["Battery power", 1, "W"],
      iBattCurrent = soc[74]                          # 25274: ["Battery current", 1, "A"],
      if iBattCurrent > 32768:
        iBattCurrent = iBattCurrent - 65536
        iBattCurrent = abs(iBattCurrent)
      else:
        iBattCurrent = -iBattCurrent

      # normally formula below shall account battery current as well, so far it is ignored (and not available when charging from grid)
      #if iBatteryVoltage > 26 :
      #  iBatterySOC = 100
      #elif iBatteryVoltage < 22 :
      #    iBatterySOC = 0
      #elif iBatteryVoltage < 22.7 :
      #    iBatterySOC = 5
      #else : 
      #  iBatterySOC = (iBatteryVoltage - 22.7) / 3.3 * 100

      return Sample(
        pvWorkState,
        pvMpptState,
        pvChargingState,
        pvVoltage,
        pvBatteryVoltage,
        pvChargerCurrent,
        pvChargerPower,
        pvRadiatorTemperature,
        pvBatteryRelay,
        pvRelay,
        pvAccumulatedPower,

        iWorkState,
        iBatteryVoltage,
        iVoltage,
        iGridVoltage,
        iPInverter,
        iPGrid,
        iPLoad,
        iLoadPercent,
        iSInverter,
        iSGrid,
        iSLoad,     
        iRadiatorTemperature
        iRelayState,
        iGridRelayState,
        iLoadRelayState,
        iAccumulatedLoadPower,
        iAccumulatedDischargerPower,
        iAccumulatedSelfusePower,
        iBattPower,
        iBattCurrent #,
      #  iBatterySOC
      )
