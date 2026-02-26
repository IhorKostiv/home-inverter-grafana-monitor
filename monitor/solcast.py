from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import requests
import json
import sys

from ups._data_ import DataStore
from ups._constants_ import logDebug

def getSolarProductionEstimate(resourceID: str, apiKey: str) -> str:
    url = f"https://api.solcast.com.au/rooftop_sites/{resourceID}/forecasts?format=json"
    headers = {"Authorization": f"Bearer {apiKey}"}
    
    response = requests.get(url, headers=headers)
    
    # Check if the request was successful
    if response.status_code == 200:
        return response.text
    else:
        print(f"Error: Received status code {response.status_code}")
        print(f"Retry after {response.headers.get('Retry-After', 'N/A')}")
        return f"Error {response.status_code}" # "error: Failed to fetch data"
    
def toJson(solarData: str):
    json_body = []
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

class Solcast(object):
    dataStore: DataStore
    MaxPowerLimit: int
    TargetPower: int
    LowPower: int
    MinPower: int
    logDetail: int = 0

    TargetDetected = None
    LowDetected = None
    MinDetected = None
    LoadAverages = {} 

    def __init__(self, ds: DataStore, maxPowerLimit: int, targetPower: int, lowPower: int, minPower: int, gridTied: list = {}, logDetail: int = 0):
        self.dataStore = ds
        self.MaxPowerLimit = maxPowerLimit
        self.TargetPower = targetPower
        self.LowPower = lowPower
        self.MinPower = minPower 
        self.logDetail = logDetail

        self.LoadAverages(gridTied)
    
    def LoadAverages(self, gridTied: list = {}):
        LoadHistory = self.dataStore.query("SELECT mean(""iPLoad"") FROM ""inverter"" WHERE time >= now() - 3d GROUP BY time(30m) tz('Europe/Kiev')")
        for table in LoadHistory: # compute average load approximation for each 30min slot using last 3 days data
            for record in table:
                t = datetime.strptime(record['time'], '%Y-%m-%dT%H:%M:%SZ').strftime('%H:%M')
                if t not in gridTied: # ignore grid tied time slots
                    if record['mean'] is None:
                        if self.logDetail >= 3:
                            print(f"!!!\a No load data for {record['time']}, skip")
                    else:
                        if t in self.LoadAverages:
                            self.LoadAverages[t] = int((self.LoadAverages[t] + int(record['mean'])) /2)
                        else:
                            self.LoadAverages[t] = int(record['mean'])
                else:
                    self.LoadAverages[t] = 2 #todo: replace with actual grid tied load

    def Calculate(self, CalcTime: datetime, Estimate: str, InternalConsumption: int):
        calcTime = CalcTime.strftime('%Y-%m-%dT%H:%M:%SZ')
        self.TargetDetected = None
        self.LowDetected = None
        self.MinDetected = None

        BatteryRemain = list(self.dataStore.query("SELECT last(\"bRemain\") * 25.6 FROM \"bms\"").get_points())[0]['last']
        print(f"{calcTime} Remain {BatteryRemain:.0f}W {BatteryRemain/51.2:.0f}% for {Estimate}")

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
                    BatteryRemain += diff
                    if BatteryRemain > self.MaxPowerLimit:
                        BatteryRemain = self.MaxPowerLimit
                        #print(f"Battery shall be fully charged at {d} UTC")
                    if self.LowDetected is None and BatteryRemain <= self.LowPower:
                        self.LowDetected = d
                        if self.logDetail >= 3:
                            print(f"Low level detected at {dtKyiv(self.LowDetected)} for {Estimate}")
                    if self.TargetDetected is None and BatteryRemain >= self.TargetPower and diff > 0:
                        self.TargetDetected = d
                        if self.logDetail >= 3:
                            print(f"Target level detected at {dtKyiv(self.TargetDetected)} for {Estimate}")
                    if BatteryRemain <= self.MinPower:
                        self.MinDetected = d
                        if self.logDetail >= 3:
                            print(f"!!!\a Battery would be depleted below {self.MinPower}W at {dtKyiv(d)}")
                        break
                    if self.logDetail >= 3:
                        print(f"{dtKyiv(d)} load {le:.0f}W gen {ge:.0f}W Remain {BatteryRemain:.0f}W {BatteryRemain/51.20:.0f}%")
            
                else:
                    if self.logDetail >= 3:
                        print(f"!!!\a {dtKyiv(d)} load ?? gen {record['Estimate']:.0f}W Remain {BatteryRemain:.0f}W {BatteryRemain/51.20:.0f}%")
                    #print(f"{d.astimezone(ZoneInfo('Europe/Kyiv')).strftime('%Y-%m-%d %H:%M')} load ? gen {record['pvEstimate']:.0f}W cre {cre:.0f} {nre:.0f}W")

# Example usage
if __name__ == "__main__":
    # refer to https://toolkit.solcast.com.au/ for details
    if len(sys.argv) == 1: # retrieve solcast data and save to DB for further use
        ds = DataStore() # "inverter.local", 8086, "root", "root", "ups")
        solcastResponse = getSolarProductionEstimate(ds.solcastResourceID, ds.solcastApiKey)
        print(datetime.now(), " ", solcastResponse)

        if solcastResponse != "":
            json = toJson(solcastResponse)
            if ds.logDetail >= 3:
                print(datetime.now(), " ", json)
            ds.write(json)
        else:
            print(datetime.now(), "Error reading forecast")
    else: # calculate which targets are met
        ds = DataStore("inverter.local", 8086, "root", "root", "ups")

        sc = Solcast(ds, ds.MaxPowerLimit, ds.TargetPower, ds.LowPower, ds.MinPower, ds.LogDetail >= logDebug)
        gridTied = ds.GridTied # os.environ.get("GRID_TIED", "").split(",") 
        #gridTied = os.environ.get("GRID_TIED", "20:00,20:30,21:00,21:30,22:00,22:30,23:00,23:30,00:00,00:30,01:00,01:30,02:00,02:30,03:00,03:30").split(",")
        if len(sys.argv) > 1:
            Estimate = sys.argv[1]
        else:
            #Estimate = 'pvEstimate10'
            #Estimate = '(pvEstimate + pvEstimate10 + pvEstimate10 + pvEstimate10)/4'
            #Estimate = os.environ.get("SOLCAST_ESTIMATE", '(pvEstimate + pvEstimate10 + pvEstimate10)/3')
            #Estimate = '(pvEstimate + pvEstimate + pvEstimate + pvEstimate10)/4'
            #Estimate = '(pvEstimate + pvEstimate10)/2'
            Estimate = 'pvEstimate' # seems reliable enough to use it as is

        sc.Calculate(datetime.now(timezone.utc), Estimate, gridTied)

        if sc.TargetDetected is not None and (sc.LowDetected is None or sc.TargetDetected < sc.LowDetected):
            print(f"Target level shall be reached first at {dtKyiv(sc.TargetDetected)} for {Estimate}, Low at {sc.LowDetected}")
        elif sc.LowDetected is not None:
            print(f"Low level could be reached first at {dtKyiv(sc.LowDetected)}, Target at {sc.TargetDetected} for {Estimate}")
            if sc.MinDetected is not None:
                print(f"!!!\a Battery would be depleted below {sc.MinPower}W at {dtKyiv(sc.MinDetected)}")
        else:
            print(f"Neither target nor low levels would be reached for {Estimate}")

        
