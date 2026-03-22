from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import requests
import json
import sys

from ups._data_ import DataStore
from ups._constants_ import logError, logWarning, logRead, logDebug
from ups import logger

def getSolarProductionEstimate(resourceID: str, apiKey: str) -> str:
    url = f"https://api.solcast.com.au/rooftop_sites/{resourceID}/forecasts?format=json"
    headers = {"Authorization": f"Bearer {apiKey}"}
    response = requests.get(url, headers=headers)
    # Check if the request was successful
    if response.status_code == 200:
        return response.text
    else:
        return f"Error {response.status_code} Retry after {response.headers.get('Retry-After', 'N/A')}" # "error: Failed to fetch data"

def toJson(solarData: str):
    json_body = [{"measurement": "solcast", "fields": {"status": "OK"}}]
    for forecast in json.loads(solarData)["forecasts"]:
        json_body.append({
            "measurement": "solcast",
            "time": forecast["period_end"],
            "fields": {
                "pvEstimate": int(float(forecast["pv_estimate"]) * 1000),
                "pvEstimate10": int(float(forecast["pv_estimate10"]) * 1000),
                "pvEstimate90": int(float(forecast["pv_estimate90"]) * 1000),
                "pvDuration": forecast["period"]
            }
        })
    return json_body

def dtKyiv(t: datetime):
    return t.astimezone(ZoneInfo("Europe/Kyiv")).strftime('%Y-%m-%d %H:%M')

class Solcast(logger):
    dataStore: DataStore
    MaxPowerLimit: int
    TargetPower: int
    LowPower: int
    MinPower: int

    TargetDetected = None
    LowDetected = None
    MinDetected = None
    Overproduction: int = 0
    LoadAverages = {} 

    def __init__(self, ds: DataStore, maxPowerLimit: int, targetPower: int, lowPower: int, minPower: int, gridTied: list = {}, logDetail: int = 0, **kwargs):
        super().__init__(logDetail = logDetail, **kwargs)
        self.dataStore = ds
        self.MaxPowerLimit = maxPowerLimit
        self.TargetPower = targetPower
        self.LowPower = lowPower
        self.MinPower = minPower 
        self.loadAverages(gridTied)

    def loadAverages(self, gridTied: list = {}):
        LoadHistory = self.dataStore.query("SELECT mean(""iPLoad"") FROM ""inverter"" WHERE time >= now() - 3d GROUP BY time(30m) tz('Europe/Kiev')")
        for table in LoadHistory: # compute average load approximation for each 30min slot using last 3 days data
            for record in table:
                t = datetime.strptime(record['time'], '%Y-%m-%dT%H:%M:%SZ').strftime('%H:%M')
                if t not in gridTied: # ignore grid tied time slots
                    if record['mean'] is None:
                        self.Log(logDebug, f"!!!\a No load data for {record['time']}, skip")
                    else:
                        if t in self.LoadAverages:
                            self.LoadAverages[t] = int((self.LoadAverages[t] + int(record['mean'])) /2)
                        else:
                            self.LoadAverages[t] = int(record['mean'])
                else:
                    self.LoadAverages[t] = 2 #todo: replace with actual grid tied load

    def Calculate(self, CalcTime: datetime, Estimate: str, InternalConsumption: int, maxChargerPower: int):
        calcTime = CalcTime.strftime('%Y-%m-%dT%H:%M:%SZ')
        self.TargetDetected = None
        self.LowDetected = None
        self.MinDetected = None
        self.Overproduction = 0

        BatteryRemain = list(self.dataStore.query("SELECT last(\"bRemain\") * 25.6 FROM \"bms\"").get_points())[0]['last']
        self.Log(logDebug, f"{calcTime} Remain {BatteryRemain:.0f}W {BatteryRemain/51.2:.0f}% for {Estimate}")

        GenerationEstimates = self.dataStore.query(f"SELECT {Estimate} as Estimate FROM \"solcast\" WHERE time >= '{calcTime}'-30m")
        for table in GenerationEstimates:
            for record in table:
                d = datetime.strptime(record['time'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
                t = d.strftime('%H:%M')
                if t in self.LoadAverages:
                    le = self.LoadAverages[t]                # Load Estimate, W
                    ge = record['Estimate']             # Generation Estimate, W
                    if d < CalcTime:                    # partial interval
                        diff = (((ge - le) * 0.5) - InternalConsumption) * (30+((d-CalcTime).total_seconds()/60))/30
                    else:                               # half hour interval 
                        diff = (ge - le - InternalConsumption) * 0.5 
                    if diff < 0:                        # discharding is faster due to inefficiencies, especially at upper SOC; todo: consider battery curve, otherwise it serves as contingency 
                        diff = diff * 1.1
                    #else:                               # charging is slower, however, at the last 5% SOC sharply goes up thus no correction
                    #    diff = diff * 0.9
                    if diff > maxChargerPower: # capping, production could be bigger than battery can absorb
                        self.Overproduction += diff - maxChargerPower
                        diff = maxChargerPower
                    BatteryRemain += diff
                    if BatteryRemain > self.MaxPowerLimit:
                        self.Overproduction += BatteryRemain - self.MaxPowerLimit
                        BatteryRemain = self.MaxPowerLimit
                        #print(f"Battery shall be fully charged at {d} UTC")
                    self.Log(logDebug, f"{dtKyiv(d)} load {le:.0f}W gen {ge:.0f}W Remain {BatteryRemain:.0f}W {BatteryRemain/51.20:.0f}%")
                    if self.LowDetected is None and BatteryRemain <= self.LowPower:
                        self.LowDetected = d
                        self.Log(logDebug, f"Low level detected by {dtKyiv(self.LowDetected)} for {Estimate}")
                    if self.TargetDetected is None and BatteryRemain >= self.TargetPower and diff > 0:
                        self.TargetDetected = d
                        self.Log(logDebug, f"Target level detected by {dtKyiv(self.TargetDetected)} for {Estimate}")
                    if BatteryRemain <= self.MinPower:
                        self.MinDetected = d
                        self.Log(logDebug, f"!!!\a Battery would be depleted below {self.MinPower}W by {dtKyiv(d)}")
                        break
                else:
                    self.Log(logDebug, f"!!!\a {dtKyiv(d)} load ?? gen {record['Estimate']:.0f}W Remain {BatteryRemain:.0f}W {BatteryRemain/51.20:.0f}%")
                    #print(f"{d.astimezone(ZoneInfo('Europe/Kyiv')).strftime('%Y-%m-%d %H:%M')} load ? gen {record['pvEstimate']:.0f}W cre {cre:.0f} {nre:.0f}W")

# Example usage
if __name__ == "__main__":
    # refer to https://toolkit.solcast.com.au/ for details
    if len(sys.argv) in [1, 6]: # retrieve solcast data and save to DB for further use
        ds = DataStore() # "inverter.local", 8086, "root", "root", "ups")
        if len(sys.argv) == 6:
            ds.LogDetail = logDebug
        ls = "OK"
        for table in ds.query("select last(status) as status from solcast"): # get last execution status and skip one reading if there was an error
            for record in table:
                ls = record["status"]
        if ls == "OK" or ls == "Skip":
            #solcastResponse = getSolarProductionEstimate(ds.solcastResourceID, ds.solcastApiKey)
            solcastResponse = '{"forecasts":[{"pv_estimate":0,"pv_estimate10":0,"pv_estimate90":0,"period_end":"2026-03-22T17:30:00.0000000Z","period":"PT30M"},{"pv_estimate":0,"pv_estimate10":0,"pv_estimate90":0,"period_end":"2026-03-22T18:00:00.0000000Z","period":"PT30M"},{"pv_estimate":0,"pv_estimate10":0,"pv_estimate90":0,"period_end":"2026-03-22T18:30:00.0000000Z","period":"PT30M"},{"pv_estimate":0,"pv_estimate10":0,"pv_estimate90":0,"period_end":"2026-03-22T19:00:00.0000000Z","period":"PT30M"},{"pv_estimate":0,"pv_estimate10":0,"pv_estimate90":0,"period_end":"2026-03-22T19:30:00.0000000Z","period":"PT30M"},{"pv_estimate":0,"pv_estimate10":0,"pv_estimate90":0,"period_end":"2026-03-22T20:00:00.0000000Z","period":"PT30M"},{"pv_estimate":0,"pv_estimate10":0,"pv_estimate90":0,"period_end":"2026-03-22T20:30:00.0000000Z","period":"PT30M"},{"pv_estimate":0,"pv_estimate10":0,"pv_estimate90":0,"period_end":"2026-03-22T21:00:00.0000000Z","period":"PT30M"},{"pv_estimate":0,"pv_estimate10":0,"pv_estimate90":0,"period_end":"2026-03-22T21:30:00.0000000Z","period":"PT30M"},{"pv_estimate":0,"pv_estimate10":0,"pv_estimate90":0,"period_end":"2026-03-22T22:00:00.0000000Z","period":"PT30M"},{"pv_estimate":0,"pv_estimate10":0,"pv_estimate90":0,"period_end":"2026-03-22T22:30:00.0000000Z","period":"PT30M"},{"pv_estimate":0,"pv_estimate10":0,"pv_estimate90":0,"period_end":"2026-03-22T23:00:00.0000000Z","period":"PT30M"},{"pv_estimate":0,"pv_estimate10":0,"pv_estimate90":0,"period_end":"2026-03-22T23:30:00.0000000Z","period":"PT30M"},{"pv_estimate":0,"pv_estimate10":0,"pv_estimate90":0,"period_end":"2026-03-23T00:00:00.0000000Z","period":"PT30M"},{"pv_estimate":0,"pv_estimate10":0,"pv_estimate90":0,"period_end":"2026-03-23T00:30:00.0000000Z","period":"PT30M"},{"pv_estimate":0,"pv_estimate10":0,"pv_estimate90":0,"period_end":"2026-03-23T01:00:00.0000000Z","period":"PT30M"},{"pv_estimate":0,"pv_estimate10":0,"pv_estimate90":0,"period_end":"2026-03-23T01:30:00.0000000Z","period":"PT30M"},{"pv_estimate":0,"pv_estimate10":0,"pv_estimate90":0,"period_end":"2026-03-23T02:00:00.0000000Z","period":"PT30M"},{"pv_estimate":0,"pv_estimate10":0,"pv_estimate90":0,"period_end":"2026-03-23T02:30:00.0000000Z","period":"PT30M"},{"pv_estimate":0,"pv_estimate10":0,"pv_estimate90":0,"period_end":"2026-03-23T03:00:00.0000000Z","period":"PT30M"},{"pv_estimate":0,"pv_estimate10":0,"pv_estimate90":0,"period_end":"2026-03-23T03:30:00.0000000Z","period":"PT30M"},{"pv_estimate":0,"pv_estimate10":0,"pv_estimate90":0,"period_end":"2026-03-23T04:00:00.0000000Z","period":"PT30M"},{"pv_estimate":0,"pv_estimate10":0,"pv_estimate90":0,"period_end":"2026-03-23T04:30:00.0000000Z","period":"PT30M"},{"pv_estimate":0.0129,"pv_estimate10":0.006,"pv_estimate90":0.0141,"period_end":"2026-03-23T05:00:00.0000000Z","period":"PT30M"},{"pv_estimate":0.0501,"pv_estimate10":0.0232,"pv_estimate90":0.052605,"period_end":"2026-03-23T05:30:00.0000000Z","period":"PT30M"},{"pv_estimate":0.0935,"pv_estimate10":0.0518,"pv_estimate90":0.098175,"period_end":"2026-03-23T06:00:00.0000000Z","period":"PT30M"},{"pv_estimate":0.1704,"pv_estimate10":0.1051,"pv_estimate90":0.17892,"period_end":"2026-03-23T06:30:00.0000000Z","period":"PT30M"},{"pv_estimate":0.2883,"pv_estimate10":0.1602,"pv_estimate90":0.3105,"period_end":"2026-03-23T07:00:00.0000000Z","period":"PT30M"},{"pv_estimate":0.4273,"pv_estimate10":0.2186,"pv_estimate90":0.5142,"period_end":"2026-03-23T07:30:00.0000000Z","period":"PT30M"},{"pv_estimate":0.5641,"pv_estimate10":0.2707,"pv_estimate90":0.7039,"period_end":"2026-03-23T08:00:00.0000000Z","period":"PT30M"},{"pv_estimate":0.6869,"pv_estimate10":0.3125,"pv_estimate90":0.8792,"period_end":"2026-03-23T08:30:00.0000000Z","period":"PT30M"},{"pv_estimate":0.7882,"pv_estimate10":0.3421,"pv_estimate90":1.0363,"period_end":"2026-03-23T09:00:00.0000000Z","period":"PT30M"},{"pv_estimate":0.8677,"pv_estimate10":0.355,"pv_estimate90":1.1793,"period_end":"2026-03-23T09:30:00.0000000Z","period":"PT30M"},{"pv_estimate":0.915,"pv_estimate10":0.3577,"pv_estimate90":1.2901,"period_end":"2026-03-23T10:00:00.0000000Z","period":"PT30M"},{"pv_estimate":0.943,"pv_estimate10":0.3559,"pv_estimate90":1.3601,"period_end":"2026-03-23T10:30:00.0000000Z","period":"PT30M"},{"pv_estimate":0.9764,"pv_estimate10":0.3519,"pv_estimate90":1.4227,"period_end":"2026-03-23T11:00:00.0000000Z","period":"PT30M"},{"pv_estimate":0.9596,"pv_estimate10":0.3266,"pv_estimate90":1.4622,"period_end":"2026-03-23T11:30:00.0000000Z","period":"PT30M"},{"pv_estimate":0.8841,"pv_estimate10":0.2825,"pv_estimate90":1.4765,"period_end":"2026-03-23T12:00:00.0000000Z","period":"PT30M"},{"pv_estimate":0.7875,"pv_estimate10":0.2421,"pv_estimate90":1.4323,"period_end":"2026-03-23T12:30:00.0000000Z","period":"PT30M"},{"pv_estimate":0.6919,"pv_estimate10":0.2042,"pv_estimate90":1.3829,"period_end":"2026-03-23T13:00:00.0000000Z","period":"PT30M"},{"pv_estimate":0.5861,"pv_estimate10":0.1688,"pv_estimate90":1.2779,"period_end":"2026-03-23T13:30:00.0000000Z","period":"PT30M"},{"pv_estimate":0.4857,"pv_estimate10":0.1387,"pv_estimate90":1.164,"period_end":"2026-03-23T14:00:00.0000000Z","period":"PT30M"},{"pv_estimate":0.3747,"pv_estimate10":0.1043,"pv_estimate90":0.9957,"period_end":"2026-03-23T14:30:00.0000000Z","period":"PT30M"},{"pv_estimate":0.2872,"pv_estimate10":0.0704,"pv_estimate90":0.8274,"period_end":"2026-03-23T15:00:00.0000000Z","period":"PT30M"},{"pv_estimate":0.1133,"pv_estimate10":0.0378,"pv_estimate90":0.5652,"period_end":"2026-03-23T15:30:00.0000000Z","period":"PT30M"},{"pv_estimate":0.0354,"pv_estimate10":0.0129,"pv_estimate90":0.3019,"period_end":"2026-03-23T16:00:00.0000000Z","period":"PT30M"},{"pv_estimate":0.0098,"pv_estimate10":0.0033,"pv_estimate90":0.0462,"period_end":"2026-03-23T16:30:00.0000000Z","period":"PT30M"},{"pv_estimate":0,"pv_estimate10":0,"pv_estimate90":0,"period_end":"2026-03-23T17:00:00.0000000Z","period":"PT30M"},{"pv_estimate":0,"pv_estimate10":0,"pv_estimate90":0,"period_end":"2026-03-23T17:30:00.0000000Z","period":"PT30M"},{"pv_estimate":0,"pv_estimate10":0,"pv_estimate90":0,"period_end":"2026-03-23T18:00:00.0000000Z","period":"PT30M"},{"pv_estimate":0,"pv_estimate10":0,"pv_estimate90":0,"period_end":"2026-03-23T18:30:00.0000000Z","period":"PT30M"},{"pv_estimate":0,"pv_estimate10":0,"pv_estimate90":0,"period_end":"2026-03-23T19:00:00.0000000Z","period":"PT30M"},{"pv_estimate":0,"pv_estimate10":0,"pv_estimate90":0,"period_end":"2026-03-23T19:30:00.0000000Z","period":"PT30M"},{"pv_estimate":0,"pv_estimate10":0,"pv_estimate90":0,"period_end":"2026-03-23T20:00:00.0000000Z","period":"PT30M"},{"pv_estimate":0,"pv_estimate10":0,"pv_estimate90":0,"period_end":"2026-03-23T20:30:00.0000000Z","period":"PT30M"},{"pv_estimate":0,"pv_estimate10":0,"pv_estimate90":0,"period_end":"2026-03-23T21:00:00.0000000Z","period":"PT30M"},{"pv_estimate":0,"pv_estimate10":0,"pv_estimate90":0,"period_end":"2026-03-23T21:30:00.0000000Z","period":"PT30M"},{"pv_estimate":0,"pv_estimate10":0,"pv_estimate90":0,"period_end":"2026-03-23T22:00:00.0000000Z","period":"PT30M"},{"pv_estimate":0,"pv_estimate10":0,"pv_estimate90":0,"period_end":"2026-03-23T22:30:00.0000000Z","period":"PT30M"},{"pv_estimate":0,"pv_estimate10":0,"pv_estimate90":0,"period_end":"2026-03-23T23:00:00.0000000Z","period":"PT30M"},{"pv_estimate":0,"pv_estimate10":0,"pv_estimate90":0,"period_end":"2026-03-23T23:30:00.0000000Z","period":"PT30M"},{"pv_estimate":0,"pv_estimate10":0,"pv_estimate90":0,"period_end":"2026-03-24T00:00:00.0000000Z","period":"PT30M"},{"pv_estimate":0,"pv_estimate10":0,"pv_estimate90":0,"period_end":"2026-03-24T00:30:00.0000000Z","period":"PT30M"},{"pv_estimate":0,"pv_estimate10":0,"pv_estimate90":0,"period_end":"2026-03-24T01:00:00.0000000Z","period":"PT30M"},{"pv_estimate":0,"pv_estimate10":0,"pv_estimate90":0,"period_end":"2026-03-24T01:30:00.0000000Z","period":"PT30M"},{"pv_estimate":0,"pv_estimate10":0,"pv_estimate90":0,"period_end":"2026-03-24T02:00:00.0000000Z","period":"PT30M"},{"pv_estimate":0,"pv_estimate10":0,"pv_estimate90":0,"period_end":"2026-03-24T02:30:00.0000000Z","period":"PT30M"},{"pv_estimate":0,"pv_estimate10":0,"pv_estimate90":0,"period_end":"2026-03-24T03:00:00.0000000Z","period":"PT30M"},{"pv_estimate":0,"pv_estimate10":0,"pv_estimate90":0,"period_end":"2026-03-24T03:30:00.0000000Z","period":"PT30M"},{"pv_estimate":0,"pv_estimate10":0,"pv_estimate90":0,"period_end":"2026-03-24T04:00:00.0000000Z","period":"PT30M"},{"pv_estimate":0,"pv_estimate10":0,"pv_estimate90":0,"period_end":"2026-03-24T04:30:00.0000000Z","period":"PT30M"},{"pv_estimate":0.0136,"pv_estimate10":0.0034,"pv_estimate90":0.0157,"period_end":"2026-03-24T05:00:00.0000000Z","period":"PT30M"},{"pv_estimate":0.047,"pv_estimate10":0.0126,"pv_estimate90":0.049350000000000005,"period_end":"2026-03-24T05:30:00.0000000Z","period":"PT30M"},{"pv_estimate":0.1026,"pv_estimate10":0.0311,"pv_estimate90":0.10773,"period_end":"2026-03-24T06:00:00.0000000Z","period":"PT30M"},{"pv_estimate":0.1744,"pv_estimate10":0.0532,"pv_estimate90":0.18312,"period_end":"2026-03-24T06:30:00.0000000Z","period":"PT30M"},{"pv_estimate":0.2729,"pv_estimate10":0.0788,"pv_estimate90":0.3079,"period_end":"2026-03-24T07:00:00.0000000Z","period":"PT30M"},{"pv_estimate":0.3754,"pv_estimate10":0.1073,"pv_estimate90":0.4959,"period_end":"2026-03-24T07:30:00.0000000Z","period":"PT30M"},{"pv_estimate":0.4722,"pv_estimate10":0.1281,"pv_estimate90":0.6789,"period_end":"2026-03-24T08:00:00.0000000Z","period":"PT30M"},{"pv_estimate":0.5883,"pv_estimate10":0.1589,"pv_estimate90":0.8635,"period_end":"2026-03-24T08:30:00.0000000Z","period":"PT30M"},{"pv_estimate":0.7251,"pv_estimate10":0.2054,"pv_estimate90":1.0198,"period_end":"2026-03-24T09:00:00.0000000Z","period":"PT30M"},{"pv_estimate":0.7943,"pv_estimate10":0.2096,"pv_estimate90":1.1598,"period_end":"2026-03-24T09:30:00.0000000Z","period":"PT30M"},{"pv_estimate":0.7641,"pv_estimate10":0.1729,"pv_estimate90":1.2644,"period_end":"2026-03-24T10:00:00.0000000Z","period":"PT30M"},{"pv_estimate":0.7339,"pv_estimate10":0.1474,"pv_estimate90":1.3392,"period_end":"2026-03-24T10:30:00.0000000Z","period":"PT30M"},{"pv_estimate":0.7217,"pv_estimate10":0.1392,"pv_estimate90":1.3973,"period_end":"2026-03-24T11:00:00.0000000Z","period":"PT30M"},{"pv_estimate":0.6855,"pv_estimate10":0.12,"pv_estimate90":1.437,"period_end":"2026-03-24T11:30:00.0000000Z","period":"PT30M"},{"pv_estimate":0.6181,"pv_estimate10":0.0925,"pv_estimate90":1.4226,"period_end":"2026-03-24T12:00:00.0000000Z","period":"PT30M"},{"pv_estimate":0.5422,"pv_estimate10":0.0705,"pv_estimate90":1.4164,"period_end":"2026-03-24T12:30:00.0000000Z","period":"PT30M"},{"pv_estimate":0.4502,"pv_estimate10":0.0552,"pv_estimate90":1.3648,"period_end":"2026-03-24T13:00:00.0000000Z","period":"PT30M"},{"pv_estimate":0.3615,"pv_estimate10":0.0481,"pv_estimate90":1.2683,"period_end":"2026-03-24T13:30:00.0000000Z","period":"PT30M"},{"pv_estimate":0.2816,"pv_estimate10":0.0449,"pv_estimate90":1.1692,"period_end":"2026-03-24T14:00:00.0000000Z","period":"PT30M"},{"pv_estimate":0.2017,"pv_estimate10":0.0355,"pv_estimate90":1.0173,"period_end":"2026-03-24T14:30:00.0000000Z","period":"PT30M"},{"pv_estimate":0.136,"pv_estimate10":0.0247,"pv_estimate90":0.8223,"period_end":"2026-03-24T15:00:00.0000000Z","period":"PT30M"},{"pv_estimate":0.0683,"pv_estimate10":0.0143,"pv_estimate90":0.6275,"period_end":"2026-03-24T15:30:00.0000000Z","period":"PT30M"},{"pv_estimate":0.0311,"pv_estimate10":0.0056,"pv_estimate90":0.3869,"period_end":"2026-03-24T16:00:00.0000000Z","period":"PT30M"},{"pv_estimate":0.0105,"pv_estimate10":0.0016,"pv_estimate90":0.1175,"period_end":"2026-03-24T16:30:00.0000000Z","period":"PT30M"},{"pv_estimate":0,"pv_estimate10":0,"pv_estimate90":0.0008,"period_end":"2026-03-24T17:00:00.0000000Z","period":"PT30M"},{"pv_estimate":0,"pv_estimate10":0,"pv_estimate90":0,"period_end":"2026-03-24T17:30:00.0000000Z","period":"PT30M"}]}'
            ds.Log(logRead, f"solcast {solcastResponse}")
            if solcastResponse != "" and solcastResponse[:5] != "Error":
                json = toJson(solcastResponse) 
                ds.Log(logDebug, json)
                ds.write(json)
                ds.Log(logRead, f"Solcast data updated for {ds.solcastResourceID}")
            else:
                ds.write([{"measurement": "solcast", "fields": {"status": solcastResponse}}])
                ds.Log(logError, f"solcast {ds.solcastResourceID} {solcastResponse}")
        else:
            ds.write([{"measurement": "solcast", "fields": {"status": "Skip"}}])
            ds.Log(logWarning, "Solcast data reading skip")
    else: # calculate which targets are met
        ds = DataStore("localhost", 8086, "root", "root", "ups1")
        gridTied = ds.GridTied # os.environ.get("GRID_TIED", "").split(",") 
        sc = Solcast(ds, ds.MaxPowerLimit, ds.TargetPower, ds.LowPower, ds.MinPower, gridTied, logDebug)
        #gridTied = os.environ.get("GRID_TIED", "21:30,22:00,22:30,23:00,23:30,00:00,00:30,01:00,01:30,02:00,02:30,03:00,03:30").split(",")
        if len(sys.argv) > 1:
            Estimate = sys.argv[1]
        else:
            #Estimate = 'pvEstimate10'
            #Estimate = '(pvEstimate + pvEstimate10 + pvEstimate10 + pvEstimate10)/4'
            #Estimate = os.environ.get("SOLCAST_ESTIMATE", '(pvEstimate + pvEstimate10 + pvEstimate10)/3')
            #Estimate = '(pvEstimate + pvEstimate + pvEstimate + pvEstimate10)/4'
            #Estimate = '(pvEstimate + pvEstimate10)/2'
            Estimate = 'pvEstimate' # seems reliable enough to use it as is

        sc.Calculate(datetime.now(timezone.utc), Estimate, 80, 40*25.6)

        if sc.TargetDetected is not None and (sc.LowDetected is None or sc.TargetDetected < sc.LowDetected):
            print(f"Target level shall be reached first at {dtKyiv(sc.TargetDetected)} for {Estimate}, Low at {sc.LowDetected} with {sc.Overproduction:.0f}W extra")
        elif sc.LowDetected is not None:
            print(f"Low level could be reached first at {dtKyiv(sc.LowDetected)}, Target at {sc.TargetDetected} for {Estimate}")
            if sc.MinDetected is not None:
                print(f"!!!\a Battery would be depleted below {sc.MinPower}W at {dtKyiv(sc.MinDetected)}")
        else:
            print(f"Neither target nor low levels would be reached for {Estimate}")