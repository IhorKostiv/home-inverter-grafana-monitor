from influxdb import InfluxDBClient
from datetime import datetime

batchSize = 1000

class Transfer:
    def __init__(self):
        self.src = None
        self.dst = None

    def openSource(self, srcHost: str, srcPort: int, srcUser: str, srcPassword: str, srcDB: str):
        self.src = InfluxDBClient(srcHost, srcPort, srcUser, srcPassword, srcDB)

    def openDestination(self, dstHost: str, dstPort: int, dstUser: str, dstPassword: str, dstDB: str):
        self.dst = InfluxDBClient(dstHost, dstPort, dstUser, dstPassword, dstDB)
        # self.dst.drop_database(dstDB) # it could be nice to migrate everything at one try but
        self.dst.create_database(dstDB)

    def copyInverterData(self, srcTableName: str, dstTableName: str, where: str = ''):
        print(datetime.now(), f" Querying all data for table Inverter {where}")
        srcTable = self.src.query(f"select * from {srcTableName} {where} order by time") # where time > '2024-10-16T00:00:00Z' and time < '2024-10-17T00:00:00Z'")
        maxTime = ''
        for table in srcTable:
            print(datetime.now(), f" Transferring {len(table)} records...", end="")
            # Transfer data line by line, converting field X to int and keeping all other fields untouched
            newData = []
            for record in table:

                f = { # must have fields
                    "pvVoltage": float(0 if record["pvVoltage"] is None else record["pvVoltage"]),
                    "pvChargerCurrent": float(0 if record["pvChargerCurrent"] is None else record["pvChargerCurrent"]), 
                    "pvChargerPower": int(0 if record["pvChargerPower"] is None else record["pvChargerPower"]),
                    "iBatteryVoltage": float(0 if record["iBatteryVoltage"] is None else record["iBatteryVoltage"]),
                    "iGridVoltage": float(0 if record["iGridVoltage"] is None else record["iGridVoltage"]),
                    "iPGrid": int(0 if record["iPGrid"] is None else -1 if record["iPGrid"] > 65000 else record["iPGrid"]),
                    "iPLoad": int(0 if record["iPLoad"] is None else -1 if record["iPLoad"] > 65000 else record["iPLoad"]),
                    "iPInverter": int(0 if record["iPInverter"] is None else -1 if record["iPInverter"] > 65000 else record["iPInverter"]),
                    "iBattPower": int(0 if record["iBattPower"] is None else record["iBattPower"])
                }
                if record["iBattPower"] is None or record["iBatteryVoltage"] is None:
                    f["iBattCurrent"] = float(0.0 if record["iBattCurrent"] is None else record["iBattCurrent"])
                else:
                    f["iBattCurrent"] = float(round(float(record["iBattPower"] / record["iBatteryVoltage"]), 1)) # record["iBattCurrent"])

                optionalValues = [ # optional fields to save space and traffic, name and null value pairs
                    ("icEnergyUse", ''),
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
                    ("pvReturnGrid", 0), # extract it from iPGrid until Nov 22 16:30
                    ("icChargerSourcePriority", ""),
                    ("BestEnergyMsg", "")
                ]
                for key, ev in optionalValues: # fille optional values in
                    if key in record and not (record[key] is None):
                        v = record[key]
                        if v != ev:
                            f[key] = v

                if record["pvError"] is None:
                    if "pvError_1" in record and not(record["pvError_1"] is None):
                        f["pvError"] = record["pvError_1"]
                else:
                    f["pvError"] = record["pvError"]

                if record["iWorkState"] is None:
                    if "iWorkState_1" in record and not(record["iWorkState_1"] is None):
                        f["iWorkState"] = record["iWorkState_1"]
                else:
                    f["iWorkState"] = record["iWorkState"]

                if record["pvWorkState"] is None:
                    pvWorkStates1 = { "Stop Mode": "Stop", "Selftest Mode": "Selftest"}
                    if record["pvWorkState_1"] in pvWorkStates1:
                        f["pvWorkState"] = pvWorkStates1[record["pvWorkState_1"]]
                    else:
                        mpptStates = { "MPPT": "MPPT", "Current limiting": "CL" }
                        pvChargingStates = { "Float charge": "F", "Absorb charge": "A"}
                        f["pvWorkState"] = f"{mpptStates[record['pvMpptState']]}-{pvChargingStates[record['pvChargingState']]}"
                else:
                    pvWorkStates = {
                        "Stop Mode, Stop, Stop":                        "Stop",
                        "Work Mode, MPPT, Absorb charge":               "MPPT-A",
                        "Selftest Mode, Stop, Stop":                    "Selftest",
                        "Work Mode, Current limiting, Absorb charge":   "CL-A",
                        "Work Mode, MPPT, Float charge":                "MPPT-F",
                        "Work Mode, Current limiting, Float charge":    "CL-F"
                    }
                    if record["pvWorkState"] in pvWorkStates:
                        f["pvWorkState"] = pvWorkStates[record["pvWorkState"]]
                    else:
                        f["pvWorkState"] = record["pvWorkState"]

                newData.append(
                    {
                        "measurement": dstTableName,
                        "time": record["time"],
                        "tags": { "uKey": record["model"] if record["uKey"] is None else record["uKey"] },
                        "fields": f
                    }
                )

                if len(newData) >= batchSize: # write in batches of 1000 records to avoid memory issues
                    self.dst.write_points(newData)
                    maxTime = newData[len(newData)-1]['time']
                    newData = []
                    print(".", end="", flush=True)

            if len(newData) > 0: # write remaining records
                self.dst.write_points(newData)
                maxTime = newData[len(newData)-1]['time']

        print(f" complete! {datetime.now()} last record {maxTime}", flush=True)
        return maxTime

    def copyBMSData(self, srcTableName: str, dstTableName: str, where: str = ''):
        print(datetime.now(), f" Querying all data for table BMS {where}")
        srcTable = self.src.query(f"select * from {srcTableName} {where} order by time") # where time > '2024-10-16T00:00:00Z' and time < '2024-10-17T00:00:00Z'")
        maxTime = ''
        for table in srcTable:
            print(datetime.now(), f" Transferring {len(table)} records...", end="")
            # Transfer data line by line, converting field X to int and keeping all other fields untouched
            newData = []
            for record in table:
                f = { # must have fields
                    "bCurrent": record["bCurrent"],
                    "bVoltage": record["bVoltage"],
                    "bSOC": record["bSOC"],
                    "bRemain": record["bRemain"],
                    "bCycles": record["bCycles"],
                }
                optionalValues = [ # optional fields to save space and traffic, name and null value pairs
                    ("bSOH", 0),
                    ("bFullCapacity", 0),
                    ("bDesignCapacity", 0),
                    ("bWarning", ''),
                    ("bProtection", ''),
                    ("bFaults", ''),
                    ("bStatus", ''),
                    ("bBalance", ''),
                    ("bVoltages1", 0.0),
                    ("bVoltages2", 0.0),
                    ("bVoltages3", 0.0),
                    ("bVoltages4", 0.0),
                    ("bVoltages5", 0.0),
                    ("bVoltages6", 0.0),
                    ("bVoltages7", 0.0),
                    ("bVoltages8", 0.0),
                    ("bTemperatures1", 0.0),
                    ("bTemperatures2", 0.0),
                    ("bMOSFETtemperature", 0),
                    ("bEnvironmentTemperature", 0)
                ]
                for key, ev in optionalValues: # fille optional values in
                    if key in record and not (record[key] is None):
                        v = record[key]
                        if v != ev:
                            f[key] = v

                newData.append(
                    {
                        "measurement": dstTableName,
                        "time": record["time"],
                        "tags": { "uKey": "MUST" },
                        "fields": f
                    }
                )

                if len(newData) >= batchSize: # write in batches of 1000 records to avoid memory issues
                    self.dst.write_points(newData)
                    maxTime = newData[len(newData)-1]['time']
                    newData = []
                    print(".", end="", flush=True)

            if len(newData) > 0: # write remaining records
                self.dst.write_points(newData)
                maxTime = newData[len(newData)-1]['time']

        print(f" complete! {datetime.now()} last record {maxTime}", flush=True)
        return maxTime

    def copyData(self, srcTableName: str, dstTableName: str, where: str = ''):
        print(datetime.now(), f" Querying all data for table {srcTableName} {where}")
        srcTable = self.src.query(f"select * from {srcTableName} {where} order by time") # where time > '2024-10-16T00:00:00Z' and time < '2024-10-17T00:00:00Z'")
        maxTime = ''
        for table in srcTable:
            print(datetime.now(), f" Transferring {len(table)} records...", end="")
            # Transfer data line by line, converting field X to int and keeping all other fields untouched
            newData = []
            for record in table:
                f = {}
                for key, value in record.items():
                    if key != "time" and key != "model" and key != "uKey": # time and tags are handled separately
                        if value is not None:
                            f[key] = value                  
                if "uKey" in record and record["uKey"] is not None:
                    newData.append(
                    {
                        "measurement": dstTableName,
                        "time": record["time"],
                        "tags": { "uKey": record["uKey"] },
                        "fields": f
                    }
                )
                else:
                    newData.append(
                    {
                        "measurement": dstTableName,
                        "time": record["time"],
                        "fields": f
                    }
                )

                if len(newData) >= batchSize: # write in batches of 1000 records to avoid memory issues
                    self.dst.write_points(newData)
                    maxTime = newData[len(newData)-1]['time']
                    newData = []
                    print(".", end="", flush=True)

            if len(newData) > 0: # write remaining records
                self.dst.write_points(newData)
                maxTime = newData[len(newData)-1]['time']

        print(f" complete! {datetime.now()} last record {maxTime}", flush=True)
        return maxTime

#todo: "rpiTemperature" shall be transfered to rPi measurement in next version

    def getWhere(self, measurement: str):
        dstTable = self.dst.query(f"select * from {measurement} order by time desc limit 1") # where time > '2024-10-16T00:00:00Z' and time < '2024-10-17T00:00:00Z'")
        maxTime = ''
        for table in dstTable:
            for record in table:
                maxTime = record["time"]
        return f"where time >= '{maxTime}'" if maxTime != '' else '' # just in case re-read last record

if __name__ == "__main__":
    # todo: possibly add command line paratemer to specify date to start import from
    tInverter = "inverter"
    tBMS = "bms"
    tForecast = "forecast"
    tSolcast = "solcast"
    tSettings = "settings"
    t = Transfer()
    t.openSource("inverter.local", "8086", "root", "root", "ups")
    t.openDestination("inverter.local", "8086", "root", "root", "ups1")

    invt = t.copyInverterData(tInverter, tInverter, t.getWhere(tInverter))
    bmst = t.copyBMSData(tBMS, tBMS, t.getWhere(tBMS))

    fct = t.copyData(tForecast, tForecast, t.getWhere(tForecast))
    sct = t.copyData(tSolcast, tSolcast, t.getWhere(tSolcast))
    stt = t.copyData(tSettings, tSettings, t.getWhere(tSettings))

    print(datetime.now(), f" Looking for new records...", flush=True)
    if invt != '':
        t.copyInverterData(tInverter, tInverter, f"where time > '{invt}'")
    if bmst != '':
        t.copyBMSData(tBMS, tBMS, f"where time > '{bmst}'")
    if sct != '':
        sct = t.copyData(tSolcast, tSolcast, f"where time > '{sct}'")
    if stt != '':
        stt = t.copyData(tSettings, tSettings, f"where time > '{stt}'")
