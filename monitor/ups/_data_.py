import os
import sys
from influxdb import InfluxDBClient
if __name__ == "__main__":
    from _constants_ import *
else:
    from ups._constants_ import *

constMeasurement = "settings"

class DataStore(object):
    def __init__(self, DB_HOST=None, DB_PORT=None, DB_USERNAME=None, DB_PASSWORD=None, DB_NAME=None):
        self._readDefaults_()
        self.client = self._getClient_(DB_HOST, DB_PORT, DB_USERNAME, DB_PASSWORD, DB_NAME)
        self.readSettings()

    def _getClient_(self, DB_HOST=None, DB_PORT=None, DB_USERNAME=None, DB_PASSWORD=None, DB_NAME=None) -> InfluxDBClient:
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

        self.InverterNode = os.environ.get("USB_DEVICE", "SIMULATOR")
        self.InverterModel = os.environ.get("INVERTER_MODEL", "") # "GreenCell", "Axioma"
        self.SolarVoltageOn = float(os.environ.get("SOLAR_VOLTAGE_ON", "0"))
        self.SolarVoltageOff = float(os.environ.get("SOLAR_VOLTAGE_OFF", "0"))
        self.PrecariousChargingEnabled = bool(os.environ.get("PRECARIOUS_CHARGING_ENABLED", "False"))
        self.GridChargingEnabled = (os.environ.get("GRID_CHARGING_ENABLED", txtGCNever))
        self.GridChargingFloat = float(os.environ.get("GRID_CHARGING_FLOAT", "0")) # 26.6
        self.GridChargingBulk = float(os.environ.get("GRID_CHARGING_BULK", "0")) # 27.9 makes 100% sharply, 27.8 up to 91% charge
        self.GridChargingEstimate = os.environ.get("GRID_CHARGING_ESTIMATE", "")

        self.bmsNode = os.environ.get("ACM_DEVICE", "SIMULATOR")
        self.bmsModel = os.environ.get("BMS_MODEL", "") # "MUST"

        self.solarForecast = os.environ.get("SOLAR_FORECAST", "") # "solcast"
        self.GridTied = os.environ.get("GRID_TIED", "").split(",")
        self.Estimate = os.environ.get("SOLCAST_ESTIMATE", '')
        self.MaxPowerLimit = int(os.environ.get("MAX_POWER_LIMIT", "0"))  # full battery capacity (5120)
        self.TargetPower = int(os.environ.get("TARGET_POWER", "0"))       # 95% approx (4900)
        self.LowPower = int(os.environ.get("LOW_POWER", "0"))             # 30% approx (1500)
        self.MinPower = int(os.environ.get("MIN_POWER", "0"))             # 20% approx (1024)
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
            for field, value in point.items():
                if field == "LogDetail":     # log detail level: 0 errors only, 1 +set commands, 2 +data, 3 +debug
                    self.LogDetail = int(value)
                elif field == "InverterModel":
                    self.InverterModel = value
                elif field == "bmsModel":
                    self.bmsModel = value
                elif field == "solarForecast":
                    self.solarForecast = value
            
    def readInverter(self, inverterModel: str):
        if inverterModel == "":
            raise Exception("Inverter model is not specified")
        s = self.query(f"SELECT last(InverterNode) as InverterNode, last(SolarVoltageOn) as SolarVoltageOn, last(SolarVoltageOff) as SolarVoltageOff FROM {constMeasurement} where uKey='{inverterModel}' ORDER BY time DESC LIMIT 1")
        for point in s.get_points():   # inverter settings
            for field, value in point.items():
                if field == "InverterNode":
                    self.InverterNode = value
                elif field == "SolarVoltageOn":
                    self.SolarVoltageOn = float(value)
                elif field == "SolarVoltageOff":
                    self.SolarVoltageOff = float(value)
            
    def readBMS(self, bmsModel: str):
        if bmsModel == "":
            raise Exception("BMS model is not specified")
        s = self.query(f"SELECT last(PrecariousChargingEnabled) as PrecariousChargingEnabled, last(GridChargingEnabled) as GridChargingEnabled, last(GridChargingFloat) as GridChargingFloat, last(GridChargingBulk) as GridChargingBulk, last(bmsNode) as bmsNode, last(MaxPowerLimit) as MaxPowerLimit, last(TargetPower) as TargetPower, last(LowPower) as LowPower, last(MinPower) as MinPower FROM {constMeasurement} where uKey='{bmsModel}' ORDER BY time DESC LIMIT 1")
        for point in s.get_points():    # battery and charging settings
            for field, value in point.items():
                if field == "PrecariousChargingEnabled":               # charging settings
                    self.PrecariousChargingEnabled = bool(value)
                elif field == "GridChargingEnabled":
                    self.GridChargingEnabled = str(value)
                elif field == "GridChargingFloat":
                    self.GridChargingFloat = float(value)
                elif field == "GridChargingBulk":
                    self.GridChargingBulk = float(value)
                elif field == "bmsNode":                                 # bms settings
                    self.bmsNode = str(value)
                elif field == "MaxPowerLimit":
                    self.MaxPowerLimit = int(value)
                elif field == "TargetPower":
                    self.TargetPower = int(value)
                elif field == "LowPower":
                    self.LowPower = int(value)
                elif field == "MinPower":
                    self.MinPower = int(value)

    def readSolarForecast(self, solarForecast: str):
        if solarForecast == "":
            raise Exception("Solar forecast model is not specified")
        s = self.query(f"SELECT last(GridTied) as GridTied, last(Estimate) as Estimate, last(GridChargingEstimate) as GridChargingEstimate, last(apiKey) as apiKey, last(resourceID) as resourceID FROM {constMeasurement} where uKey='{solarForecast}' ORDER BY time DESC LIMIT 1")    
        for point in s.get_points():    # solar production settings
            for field, value in point.items():
                if field == "GridTied":
                    self.GridTied = value.split(",")
                elif field == "Estimate":
                    self.Estimate = value
                elif field == "GridChargingEstimate":
                    self.GridChargingEstimate = value
                elif field == "apiKey":
                    self.solcastApiKey = value
                elif field == "resourceID":
                    self.solcastResourceID = value

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

    def saveSettingsInverter(self, inverterModel: str, inverterNode: str, solarVoltageOn: float, solarVoltageOff: float):
        if inverterModel == "":
            raise Exception("Inverter model is not specified")
        if inverterModel != self.InverterModel or inverterNode != self.InverterNode or solarVoltageOn != self.SolarVoltageOn or solarVoltageOff != self.SolarVoltageOff:
            json = [
                {
                    "measurement": constMeasurement,
                    "tags": { "uKey": inverterModel },
                    "fields": {
                        "InverterNode": inverterNode,
                        "SolarVoltageOn": solarVoltageOn,
                        "SolarVoltageOff": solarVoltageOff}
                }
            ]
            self.write(json)

    def saveSettingsBMS(self, bmsModel: str, bmsNode: str, precariousChargingEnabled: bool, gridChargingEnabled: str, gridChargingFloat: float, gridChargingBulk: float, maxPowerLimit: int, targetPower: int, lowPower: int, minPower: int):
        if bmsModel == "":
            raise Exception("BMS model is not specified")
        if bmsModel != self.bmsModel or precariousChargingEnabled != self.PrecariousChargingEnabled or gridChargingEnabled != self.GridChargingEnabled or gridChargingFloat != self.GridChargingFloat or gridChargingBulk != self.GridChargingBulk or bmsNode != self.bmsNode or maxPowerLimit != self.MaxPowerLimit or targetPower != self.TargetPower or lowPower != self.LowPower or minPower != self.MinPower:
            json = [
                {
                    "measurement": constMeasurement,
                    "tags": { "uKey": bmsModel },
                    "fields": {
                        "PrecariousChargingEnabled": precariousChargingEnabled,
                        "GridChargingEnabled": gridChargingEnabled,
                        "GridChargingFloat": gridChargingFloat,
                        "GridChargingBulk": gridChargingBulk,
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

if __name__ == "__main__":
    ds: DataStore = DataStore("inverter.local", 8086, "root", "root", "ups")
    #print(f"LogDetail {ds.LogDetail}")
    #print(f"InverterNode {ds.InverterNode} Model {ds.InverterModel} SolarVoltageOn {ds.SolarVoltageOn} SolarVoltageOff {ds.SolarVoltageOff}")
    #print(f"PrecariousChargingEnabled {ds.PrecariousChargingEnabled} GridChargingEnabled {ds.GridChargingEnabled} GridChargingFloat {ds.GridChargingFloat} GridChargingBulk {ds.GridChargingBulk}")
    #print(f"bmsNode {ds.bmsNode} bmsModel {ds.bmsModel} MaxPowerLimit {ds.MaxPowerLimit} TargetPower {ds.TargetPower} LowPower {ds.LowPower} MinPower {ds.MinPower}")
    #print(f"GridTied {ds.GridTied} Estimate {ds.Estimate} GridChargingEstimate {ds.GridChargingEstimate} solcastApiKey {ds.solcastApiKey} solcastResourceID {ds.solcastResourceID}")

    if len(sys.argv) > 2:
        if sys.argv[1] in {"Axioma", "GreenCell"} and len(sys.argv) == 5:
            # saveSettingsInverter(self, inverterModel: str, inverterNode: str, solarVoltageOn: float, solarVoltageOff: float)
            ds.saveSettingsInverter(sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]))
        elif sys.argv[1] == "MUST" and len(sys.argv) == 11:
            # saveSettingsBMS(self, bmsModel: str, bmsNode: str, precariousChargingEnabled: bool, gridChargingEnabled: str, gridChargingFloat: float, gridChargingBulk: float, maxPowerLimit: int, targetPower: int, lowPower: int, minPower: int) 
            ds.saveSettingsBMS(sys.argv[1], sys.argv[2], bool(sys.argv[3]), sys.argv[4], float(sys.argv[5]), float(sys.argv[6]), int(sys.argv[7]), int(sys.argv[8]), int(sys.argv[9]), int(sys.argv[10]))
        elif sys.argv[1] == "solcast" and len(sys.argv) >= 5:
            # saveSettingsSolarForecast(self, solarForecast: str, gridTied: list, estimate: str, gridChargingEstimate: str, solcastApiKey: str = "", solcastResourceID: str = "")
            ds.saveSettingsSolarForecast(sys.argv[1], sys.argv[2].split(","), sys.argv[3], sys.argv[4], sys.argv[5] if len(sys.argv) > 5 else "", sys.argv[6] if len(sys.argv) > 6 else "")
        elif int(sys.argv[1]) in {0, 1, 2, 3} and len(sys.argv) == 5:
            # saveSettingsGeneral(self, logDetail: int, inverterModel: str, bmsModel: str, solarForecast: str)
            ds.saveSettingsGeneral(int(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4])
        else:
            print(f"Unknown settings type {sys.argv[1]}")
            print("Possible scenarios:")
            print("python3 _data_.py InverterModel InverterNode SolarVoltageOn SolarVoltageOff")
            print(f"python3 _data_.py {ds.InverterModel} {ds.InverterNode} {ds.SolarVoltageOn} {ds.SolarVoltageOff}")
            print("\npython3 _data_.py BMSModel BMSNode PrecariousChargingEnabled GridChargingEnabled GridChargingFloat GridChargingBulk MaxPowerLimit TargetPower LowPower MinPower")
            print(f"python3 _data_.py {ds.bmsModel} {ds.bmsNode} {ds.PrecariousChargingEnabled} {ds.GridChargingEnabled} {ds.GridChargingFloat} {ds.GridChargingBulk} {ds.MaxPowerLimit} {ds.TargetPower} {ds.LowPower} {ds.MinPower}")
            print("\npython3 _data_.py solcast GridTied Estimate GridChargingEstimate SolcastApiKey SolcastResourceID")
            # todo: solcast can have multiple fields, so that Resource IDs shall be a list
            print(f"python3 _data_.py {ds.solarForecast} {','.join(ds.GridTied)} {ds.Estimate} {ds.GridChargingEstimate} {ds.solcastApiKey} {ds.solcastResourceID}")
            print("\npython3 _data_.py LogDetail InverterModel BMSModel SolarForecast")
            print(f"python3 _data_.py {ds.LogDetail} {ds.InverterModel} {ds.bmsModel} {ds.solarForecast}")
    else:
        ds.saveSettingsInverter(inverterModel="Axioma", inverterNode="/dev/ttyUSB0", solarVoltageOn=140, solarVoltageOff=100)
        ds.saveSettingsBMS(bmsModel="MUST", bmsNode="/dev/ttyACM0", precariousChargingEnabled=True, gridChargingEnabled=txtGCAlways, gridChargingFloat=26.6, gridChargingBulk=27.9, maxPowerLimit=5120, targetPower=4900, lowPower=1500, minPower=1024)
        ds.saveSettingsSolarForecast(solarForecast="solcast", gridTied=[''], estimate="(pvEstimate+pvEstimate10)/2", gridChargingEstimate="pvEstimate")
        ds.saveSettingsGeneral(logDetail=logRead, inverterModel="Axioma", bmsModel="MUST", solarForecast="solcast")
    '''
    ds.saveSettingsInverter("GreenCell", "/dev/ttyUSB0", 70, 50)
    ds.saveSettingsBMS("MUST", "/dev/ttyACM0", False, True, 26.6, 27.9, 5120, 4900, 1500, 1024)
    ds.saveSettingsSolarForecast("solcast", [], "(pvEstimate+pvEstimate10)/2", "pvEstimate")
    ds.saveSettingsGeneral(logRead, "GreenCell", "MUST", "solcast")
    '''