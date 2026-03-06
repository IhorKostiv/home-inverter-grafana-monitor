import os
import sys
from influxdb import InfluxDBClient
if __name__ == "__main__":
    from __init__ import logger
    from _constants_ import *
else:
    from ups import logger
    from ups._constants_ import *

constMeasurement = "settings"

class DataStore(logger):
    def __init__(self, DB_HOST=None, DB_PORT=None, DB_USERNAME=None, DB_PASSWORD=None, DB_NAME=None):
        self._readDefaults_()
        self.client = self._getClient_(DB_HOST, DB_PORT, DB_USERNAME, DB_PASSWORD, DB_NAME)
        self.readSettings()

    def _getClient_(self, DB_HOST=None, DB_PORT=None, DB_USERNAME=None, DB_PASSWORD=None, DB_NAME=None) -> InfluxDBClient:
        # when unit is directly called, paramenetrs are hardcoded ans command line is used to set values in DB
        # from Docker container environmebt variables are used
        # when monitor is called then connection parameters are in command string
        if DB_HOST is not None and DB_PORT is not None and DB_USERNAME is not None and DB_PASSWORD is not None and DB_NAME is not None:
            pass
        elif len(sys.argv) >= 6:
            DB_HOST = sys.argv[1]
            DB_PORT = int(sys.argv[2])
            DB_USERNAME = sys.argv[3]
            DB_PASSWORD = sys.argv[4]
            DB_NAME = sys.argv[5]
        elif "DB_HOST" in os.environ and "DB_PORT" in os.environ and "DB_USERNAME" in os.environ and "DB_PASSWORD" in os.environ and "DB_NAME" in os.environ:
            DB_HOST = os.environ.get("DB_HOST")
            DB_PORT = int(os.environ.get("DB_PORT"))
            DB_USERNAME = os.environ.get("DB_USERNAME")
            DB_PASSWORD = os.environ.get("DB_PASSWORD")
            DB_NAME = os.environ.get("DB_NAME")
        else:
            print("\aPlease provide database connection parameters as command line arguments or environment variables")
            print(f"Usage: python3 {os.path.basename(sys.argv[0])} <DB_HOST> <DB_PORT> <DB_USERNAME> <DB_PASSWORD> <DB_NAME>")
            print(f"Example: python3 {os.path.basename(sys.argv[0])} inverter.local 8086 root root ups")
            print("Or set environment variables DB_HOST, DB_PORT, DB_USERNAME, DB_PASSWORD, DB_NAME")
            exit(1)

        return InfluxDBClient(DB_HOST, DB_PORT, DB_USERNAME, DB_PASSWORD, DB_NAME)

    def _readDefaults_(self):
        self.LogDetail = int(os.environ.get("LOG_DETAIL", "0")) # 0 errors only, 1 +set commands, 2 +data, 3 +debug
        self.InverterModel = os.environ.get("INVERTER_MODEL", "") # "GreenCell", "Axioma"
        self.bmsModel = os.environ.get("BMS_MODEL", "") # "MUST"
        self.solarForecast = os.environ.get("SOLAR_FORECAST", "") # "solcast"
        # Inverter settings
        self.InverterNode = os.environ.get("USB_DEVICE", "SIMULATOR")
        self.SolarVoltageOn = float(os.environ.get("SOLAR_VOLTAGE_ON", "0"))
        self.SolarVoltageOff = float(os.environ.get("SOLAR_VOLTAGE_OFF", "0"))
        self.MaxUtiChargeCurent = int(os.environ.get("MAX_UTI_CHARGE_CURRENT", "0"))
        self.MinUtiChargeCurent = int(os.environ.get("MIN_UTI_CHARGE_CURRENT", "0"))
        self.PrecariousChargingEnabled = bool(os.environ.get("PRECARIOUS_CHARGING_ENABLED", "False") == "True")
        self.GridChargingEnabled = (os.environ.get("GRID_CHARGING_ENABLED", txtGCNever))
        self.GridChargingFloat = float(os.environ.get("GRID_CHARGING_FLOAT", "0")) # 26.6
        self.GridChargingBulk = float(os.environ.get("GRID_CHARGING_BULK", "0")) # 27.9 makes 100% sharply, 27.8 up to 91% charge
        # BMS settings
        self.bmsNode = os.environ.get("ACM_DEVICE", "SIMULATOR")
        self.MaxPowerLimit = int(os.environ.get("MAX_POWER_LIMIT", "0"))  # full battery capacity (5120)
        self.TargetPower = int(os.environ.get("TARGET_POWER", "0"))       # 95% approx (4900)
        self.LowPower = int(os.environ.get("LOW_POWER", "0"))             # 30% approx (1500)
        self.MinPower = int(os.environ.get("MIN_POWER", "0"))             # 20% approx (1024)
        # Solar forecast settings
        self.GridTied = os.environ.get("GRID_TIED", "").split(",")
        self.Estimate = os.environ.get("SOLCAST_ESTIMATE", '')
        self.GridChargingEstimate = os.environ.get("GRID_CHARGING_ESTIMATE", "")
        self.solcastApiKey = ""
        self.solcastResourceID = ""

    def readSettings(self):
        self.readGeneral()
        if self.InverterModel != "":
            self.readInverter(self.InverterModel)
        if self.bmsModel != "":
            self.readBMS(self.bmsModel)
        if self.solarForecast != "":
            self.readSolarForecast(self.solarForecast)

    def readGeneral(self):
        s = self.query(f"SELECT last(LogDetail) as LogDetail, last(InverterModel) as InverterModel, last(bmsModel) as bmsModel, last(solarForecast) as solarForecast FROM {constMeasurement} where uKey='General' ORDER BY time DESC LIMIT 1")
        for point in s.get_points():    # general settings and keys for rest of settings
            self.LogDetail = int(point["LogDetail"]) # log detail level: 0 errors only, 1 +set commands, 2 +data, 3 +debug
            self.InverterModel = point["InverterModel"]
            self.bmsModel = point["bmsModel"]
            self.solarForecast = point["solarForecast"]
            break

    def readInverter(self, inverterModel: str):
        if inverterModel == "":
            raise Exception("Inverter model is not specified")
        s = self.query(f"SELECT last(InverterNode) as InverterNode, last(SolarVoltageOn) as SolarVoltageOn, last(SolarVoltageOff) as SolarVoltageOff, last(PrecariousChargingEnabled) as PrecariousChargingEnabled, last(GridChargingEnabled) as GridChargingEnabled, last(GridChargingFloat) as GridChargingFloat, last(GridChargingBulk) as GridChargingBulk, last(MaxUtiChargeCurent) as MaxUtiChargeCurent, last(MinUtiChargeCurent) as MinUtiChargeCurent FROM {constMeasurement} where uKey='{inverterModel}' ORDER BY time DESC LIMIT 1")
        for point in s.get_points():   # inverter settings
            self.InverterNode = point["InverterNode"]
            self.SolarVoltageOn = float(point["SolarVoltageOn"])
            self.SolarVoltageOff = float(point["SolarVoltageOff"])
            self.MaxUtiChargeCurent = int(point["MaxUtiChargeCurent"]) #if "MaxUtiChargeCurent" in point and point["MaxUtiChargeCurent"] is not None else self.MaxUtiChargeCurent
            self.MinUtiChargeCurent = int(point["MinUtiChargeCurent"]) #if "MinUtiChargeCurent" in point and point["MinUtiChargeCurent"] is not None else self.MinUtiChargeCurent
            self.PrecariousChargingEnabled = bool(str(point["PrecariousChargingEnabled"]).lower() == "true") #if "PrecariousChargingEnabled" in point and point["PrecariousChargingEnabled"] is not None else self.PrecariousChargingEnabled
            self.GridChargingEnabled = str(point["GridChargingEnabled"]) #if "GridChargingEnabled" in point and point["GridChargingEnabled"] is not None else self.GridChargingEnabled
            self.GridChargingFloat = float(point["GridChargingFloat"]) #if "GridChargingFloat" in point and point["GridChargingFloat"] is not None else self.GridChargingFloat
            self.GridChargingBulk = float(point["GridChargingBulk"]) #if "GridChargingBulk" in point and point["GridChargingBulk"] is not None else self.GridChargingBulk
            break

    def readBMS(self, bmsModel: str):
        if bmsModel == "":
            raise Exception("BMS model is not specified")
        s = self.query(f"SELECT last(bmsNode) as bmsNode, last(MaxPowerLimit) as MaxPowerLimit, last(TargetPower) as TargetPower, last(LowPower) as LowPower, last(MinPower) as MinPower FROM {constMeasurement} where uKey='{bmsModel}' ORDER BY time DESC LIMIT 1")
        for point in s.get_points():    # battery and charging settings
            self.bmsNode = str(point["bmsNode"])
            self.MaxPowerLimit = int(point["MaxPowerLimit"])
            self.TargetPower = int(point["TargetPower"])
            self.LowPower = int(point["LowPower"])
            self.MinPower = int(point["MinPower"])
            break

    def readSolarForecast(self, solarForecast: str):
        if solarForecast == "":
            raise Exception("Solar forecast source is not specified")
        s = self.query(f"SELECT last(GridTied) as GridTied, last(Estimate) as Estimate, last(GridChargingEstimate) as GridChargingEstimate, last(apiKey) as apiKey, last(resourceID) as resourceID FROM {constMeasurement} where uKey='{solarForecast}' ORDER BY time DESC LIMIT 1")    
        for point in s.get_points():    # solar production settings
            self.GridTied = point["GridTied"].split(",")
            self.Estimate = str(point["Estimate"])
            self.GridChargingEstimate = str(point["GridChargingEstimate"])
            self.solcastApiKey = str(point["apiKey"])
            self.solcastResourceID = str(point["resourceID"])
            break

    def query(self, query: str):
        return self.client.query(query)     
    def write(self, json_body: dict):
        self.client.write_points(json_body)

    def saveSettingsGeneral(self, logDetail: int, inverterModel: str, bmsModel: str, solarForecast: str):
        if logDetail != self.LogDetail or inverterModel != self.InverterModel or bmsModel != self.bmsModel or solarForecast != self.solarForecast:
            json = [
                {
                    "measurement": constMeasurement,
                    "tags": { "uKey": "General" },
                    "fields": {
                        "LogDetail": logDetail,
                        "InverterModel": inverterModel,
                        "bmsModel": bmsModel,
                        "solarForecast": solarForecast}
                }
            ]
            self.write(json)

    def saveSettingsInverter(self, inverterModel: str, inverterNode: str, solarVoltageOn: float, solarVoltageOff: float, MaxUtiChargeCurent: int, MinUtiChargeCurent: int, precariousChargingEnabled: bool, gridChargingEnabled: str, gridChargingFloat: float, gridChargingBulk: float):
        if inverterModel == "":
            raise Exception("Inverter model is not specified")
        if (solarVoltageOn != 0 and solarVoltageOn <= solarVoltageOff) or solarVoltageOn < 0 or solarVoltageOff < 0:
            raise Exception(f"Invalid inverter solar on/off settings, expected {solarVoltageOn} > {solarVoltageOff}")
        if MaxUtiChargeCurent < MinUtiChargeCurent:
            raise Exception(f"Invalid inverter charge current, expected {MaxUtiChargeCurent} > {MinUtiChargeCurent}")
        if precariousChargingEnabled and gridChargingFloat >= gridChargingBulk:
            raise Exception(f"Invalid precarious charging settings, expected {gridChargingFloat} < {gridChargingBulk}")
        if inverterModel != self.InverterModel or inverterNode != self.InverterNode or solarVoltageOn != self.SolarVoltageOn or solarVoltageOff != self.SolarVoltageOff  or MaxUtiChargeCurent != self.MaxUtiChargeCurent or MinUtiChargeCurent != self.MinUtiChargeCurent or precariousChargingEnabled != self.PrecariousChargingEnabled or gridChargingEnabled != self.GridChargingEnabled or gridChargingFloat != self.GridChargingFloat or gridChargingBulk != self.GridChargingBulk:
            json = [
                {
                    "measurement": constMeasurement,
                    "tags": { "uKey": inverterModel },
                    "fields": {
                        "InverterNode": inverterNode,
                        "SolarVoltageOn": solarVoltageOn,
                        "SolarVoltageOff": solarVoltageOff,
                        "MaxUtiChargeCurent": MaxUtiChargeCurent,
                        "MinUtiChargeCurent": MinUtiChargeCurent,
                        "PrecariousChargingEnabled": precariousChargingEnabled,
                        "GridChargingEnabled": gridChargingEnabled,
                        "GridChargingFloat": gridChargingFloat,
                        "GridChargingBulk": gridChargingBulk}
                }
            ]
            self.write(json)

    def saveSettingsBMS(self, bmsModel: str, bmsNode: str, maxPowerLimit: int, targetPower: int, lowPower: int, minPower: int):
        if bmsModel == "":
            raise Exception("BMS model is not specified")
        if not ((maxPowerLimit == 0 and targetPower == 0 and lowPower == 0 and minPower == 0) or (maxPowerLimit > targetPower > lowPower > minPower)):
            raise Exception(f"Invalid BMS settings, expected {maxPowerLimit} > {targetPower} > {lowPower} > {minPower}")
        if bmsModel != self.bmsModel or bmsNode != self.bmsNode or maxPowerLimit != self.MaxPowerLimit or targetPower != self.TargetPower or lowPower != self.LowPower or minPower != self.MinPower:
            json = [
                {
                    "measurement": constMeasurement,
                    "tags": { "uKey": bmsModel },
                    "fields": {
                        "bmsNode": bmsNode,
                        "MaxPowerLimit": maxPowerLimit,
                        "TargetPower": targetPower,
                        "LowPower": lowPower,
                        "MinPower": minPower}
                }
            ]
            self.write(json)

    def saveSettingsSolarForecast(self, solarForecast: str, gridTied: list, estimate: str, gridChargingEstimate: str, solcastApiKey: str = "", solcastResourceID: str = ""):
        if solarForecast == "":
            raise Exception("Solar forecast is not specified")
        if solarForecast != self.solarForecast or gridTied != self.GridTied or estimate != self.Estimate or gridChargingEstimate != self.GridChargingEstimate or (solcastApiKey != "" and solcastApiKey != self.solcastApiKey) or (solcastResourceID != "" and solcastResourceID != self.solcastResourceID):
            json = [
               {
                    "measurement": constMeasurement,
                    "tags": { "uKey": solarForecast },
                    "fields": {
                        "GridTied": ",".join(gridTied),
                        "Estimate": estimate,
                        "GridChargingEstimate": gridChargingEstimate} 
                }
            ]
            if solcastApiKey != "":
                json[0]["fields"]["apiKey"] = solcastApiKey
            if solcastResourceID != "":
                json[0]["fields"]["resourceID"] = solcastResourceID
            self.write(json)

    def setDefaultSettings(self, solcastApiKey: str, solcastResourceID: str):
        ds.saveSettingsInverter(inverterModel="Axioma", inverterNode="/dev/ttyUSB0", solarVoltageOn=140.0, solarVoltageOff=100.0, MaxUtiChargeCurent=20, MinUtiChargeCurent=2, precariousChargingEnabled=True, gridChargingEnabled=txtGCEmergency, gridChargingFloat=26.6, gridChargingBulk=27.9)
        #ds.saveSettingsInverter(inverterModel="GreenCell", inverterNode="/dev/ttyUSB0", solarVoltageOn=70, solarVoltageOff=50, MaxUtiChargeCurent=30, MinUtiChargeCurent=20, precariousChargingEnabled=False, gridChargingEnabled=txtGCEmergency, gridChargingFloat=26.6, gridChargingBulk=27.9)
        #ds.saveSettingsInverter(inverterModel="GreenCell", inverterNode="/dev/ttyUSB0", solarVoltageOn=43, solarVoltageOff=30, MaxUtiChargeCurent=20, MinUtiChargeCurent=10, precariousChargingEnabled=False, gridChargingEnabled=txtGCNever, gridChargingFloat=13.3, gridChargingBulk=13.9) 
        # SOLAR_VOLTAGE_ON: 43 #43 #44 approx. 90% of field idle voltage 43-44 summer 46-47 winter      SOLAR_VOLTAGE_OFF: 30 #37 #30 #35 #15 approx. field MPPT voltage 30 summer 35 winter
        #ds.saveSettingsBMS(bmsModel="", bmsNode="SIMULATOR", maxPowerLimit=0, targetPower=0, lowPower=0, minPower=0)
        ds.saveSettingsBMS(bmsModel="MUST", bmsNode="/dev/ttyACM0", maxPowerLimit=5120, targetPower=4950, lowPower=1500, minPower=1024)
        # it is not expected to hard code API Key or Resource ID, only pass as paramenets for security reasons
        ds.saveSettingsSolarForecast(solarForecast="solcast", gridTied=[''], estimate="(pvEstimate+pvEstimate10)/2", gridChargingEstimate="pvEstimate", solcastApiKey=solcastApiKey, solcastResourceID=solcastResourceID)
        ds.saveSettingsGeneral(logDetail=logRead, inverterModel="Axioma", bmsModel="MUST", solarForecast="solcast")
        #ds.saveSettingsGeneral(logDetail=logRead, inverterModel="GreenCell", bmsModel="", solarForecast="solcast")

if __name__ == "__main__":
    server = "localhost"
    print(f"Open {server}")
    ds: DataStore = DataStore(server, 8086, "root", "root", "ups1")
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "CLEAR": # delete settings table to reset values
            ds.query(f"DROP MEASUREMENT settings")
            ds.setDefaultSettings(sys.argv[2] if len(sys.argv) > 2 else "", sys.argv[3] if len(sys.argv) > 3 else "")
            print("Settings cleared and reset to defaults")
        elif sys.argv[1] in {"Axioma", "GreenCell"} and len(sys.argv) == 11:
            # saveSettingsInverter(self, inverterModel: str, inverterNode: str, solarVoltageOn: float, solarVoltageOff: float, precariousChargingEnabled: bool, gridChargingEnabled: str, gridChargingFloat: float, gridChargingBulk: float)
            ds.saveSettingsInverter(sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4]), int(sys.argv[5]), int(sys.argv[6]), bool(sys.argv[7] == "True"), sys.argv[8], float(sys.argv[9]), float(sys.argv[10]))
        elif sys.argv[1] == "MUST" and len(sys.argv) == 7:
            # saveSettingsBMS(self, bmsModel: str, bmsNode: str, maxPowerLimit: int, targetPower: int, lowPower: int, minPower: int) 
            ds.saveSettingsBMS(sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]), int(sys.argv[6]))
        elif sys.argv[1] == "solcast" and len(sys.argv) >= 5:
            # saveSettingsSolarForecast(self, solarForecast: str, gridTied: list, estimate: str, gridChargingEstimate: str, solcastApiKey: str = "", solcastResourceID: str = "")
            ds.saveSettingsSolarForecast(sys.argv[1], sys.argv[2].split(","), sys.argv[3], sys.argv[4], sys.argv[5] if len(sys.argv) > 5 else "", sys.argv[6] if len(sys.argv) > 6 else "")
        elif sys.argv[1] in {"0", "1", "2", "3"} and len(sys.argv) == 5:
            # saveSettingsGeneral(self, logDetail: int, inverterModel: str, bmsModel: str, solarForecast: str)
            ds.saveSettingsGeneral(int(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4])
        else:
            print(f"Unknown settings command {sys.argv[1]}")
    else:
        print("Possible scenarios:")
        print("python3 _data_.py InverterModel InverterNode SolarVoltageOn SolarVoltageOff MaxUtiChargeCurent MinUtiChargeCurent PrecariousChargingEnabled GridChargingEnabled GridChargingFloat GridChargingBulk")
        print(f"python3 _data_.py {ds.InverterModel} {ds.InverterNode} {ds.SolarVoltageOn} {ds.SolarVoltageOff} {ds.MaxUtiChargeCurent} {ds.MinUtiChargeCurent} {ds.PrecariousChargingEnabled} {ds.GridChargingEnabled} {ds.GridChargingFloat} {ds.GridChargingBulk}")
        print("\npython3 _data_.py BMSModel BMSNode MaxPowerLimit TargetPower LowPower MinPower")
        print(f"python3 _data_.py {ds.bmsModel} {ds.bmsNode} {ds.MaxPowerLimit} {ds.TargetPower} {ds.LowPower} {ds.MinPower}")
        # todo: solcast can have multiple fields, so that Resource IDs shall be a list
        print("\npython3 _data_.py solcast GridTied Estimate GridChargingEstimate SolcastApiKey SolcastResourceID")
        print(f'python3 _data_.py {ds.solarForecast} "{",".join(ds.GridTied)}" "{ds.Estimate}" "{ds.GridChargingEstimate}" {ds.solcastApiKey} {ds.solcastResourceID}')
        print("\npython3 _data_.py LogDetail InverterModel BMSModel SolarForecast")
        print(f'python3 _data_.py {ds.LogDetail} {ds.InverterModel} "{ds.bmsModel}" "{ds.solarForecast}"')
