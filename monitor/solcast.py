import datetime
import pytz

from influxdb import InfluxDBClient
#from influxdb_client.client.write_api import SYNCHRONOUS, ASYNCHRONOUS
from datetime import datetime, timezone
import requests
import json
import os
import sys

def getClient() -> InfluxDBClient:
    DB_HOST = os.environ.get("DB_HOST", "inverter.local")
    DB_PORT = int(os.environ.get("DB_PORT", "8086"))
    DB_USERNAME = os.environ.get("DB_USERNAME", "root")
    DB_PASSWORD = os.environ.get("DB_PASSWORD", "root")
    DB_NAME = os.environ.get("DB_NAME", "ups")
    client = InfluxDBClient(DB_HOST, DB_PORT, DB_USERNAME, DB_PASSWORD, DB_NAME)
    return client

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
def saveSolarProductionEstimateToDB(solarData: str, client: InfluxDBClient, logDetail: int):
    solarDataJson = json.loads(solarData)
    forecasts = solarDataJson["forecasts"]
    for forecast in forecasts:
        json_body = [{
            "measurement": "solcast",
            "time": forecast["period_end"],
            "fields": {
                "pvEstimate": int(float(forecast["pv_estimate"]) * 1000),
                "pvEstimate10": int(float(forecast["pv_estimate10"]) * 1000),
                "pvEstimate90": int(float(forecast["pv_estimate90"]) * 1000),
                "pvDuration": forecast["period"]
            }
        }]
        if logDetail >= 3:
            print(datetime.now(), " ", json_body)

        client.write_points(json_body)

def dtKyiv(t:datetime):
    return t.astimezone(pytz.timezone('Europe/Kyiv')).strftime('%Y-%m-%d %H:%M')

class Solcast(object):
    client: InfluxDBClient
    MaxPowerLimit: int
    TargetPower: int
    LowPower: int
    MinPower: int
    logDetail: int = 0

    TargetDetected = None
    LowDetected = None
    MinDetected = None
    LoadAverages = {} 

    def __init__(self, client: InfluxDBClient, maxPowerLimit: int, targetPower: int, lowPower: int, minPower: int, gridTied: list = {}, logDetail: int = 0):
        self.client = client
        self.MaxPowerLimit = maxPowerLimit
        self.TargetPower = targetPower
        self.LowPower = lowPower
        self.MinPower = minPower 
        self.logDetail = logDetail

        self.LoadAverages(gridTied)
    
    def LoadAverages(self, gridTied: list = {}):
        LoadHistory = self.client.query("SELECT mean(""iPLoad"") FROM ""inverter"" WHERE time >= now() - 3d GROUP BY time(30m) tz('Europe/Kiev')")
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

        BatteryRemain = list(self.client.query("SELECT last(\"bRemain\") * 25.6 FROM \"bms\"").get_points())[0]['last']
        print(f"{calcTime} Remain {BatteryRemain:.0f}W {BatteryRemain/51.2:.0f}% for {Estimate}")

        GenerationEstimates = self.client.query(f"SELECT {Estimate} as Estimate FROM \"solcast\" WHERE time >= '{calcTime}'-30m")

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


''' Old code for local estimation, not used now
def pvEstimate(currentTime: datetime, solarData) -> int:

    p1 = p2 = -2
    t1 = t2 = currentTime
    sd = solarData["forecasts"]
    for i, t in enumerate(sd):
        p = t["pv_estimate"]
        tt = parser.parse(t["period_end"])
        #print(f"power {p} @ {tt} {tz}")
        if currentTime > tt:
            p1 = p
            t1 = tt
        else:
            if currentTime <= tt:
                p2 = p
                t2 = tt
                break

#        print(f"index {i} time {t} estimate {p}")

    d1 = currentTime - t1
 #   d2 = t2 - current_time
    d = t2 - t1

    if p1 > 0:
        avg = p1 + ((p2 - p1) * d1.total_seconds() / d.total_seconds()) # linear approximation
    else:
        avg = p2

    print(f"estimate {avg} @ {currentTime} between {p1} @ {t1} and {p2} @ {t2}")
    return int(avg)
def next30min():
    now = datetime.now(timezone.utc)
    # Calculate how many minutes to add to reach the next 30-minute mark
    minutes_to_add = (30 - now.minute % 30) % 30
    if minutes_to_add == 0 and now.second == 0 and now.microsecond == 0:
        rounded = now
    else:
        rounded = now.replace(second=0, microsecond=0) + timedelta(minutes=minutes_to_add)
    return rounded.strftime('%Y-%m-%dT%H:%M:%S.0000000Z')
def prev30min():
    now = datetime.now(timezone.utc)
    # Calculate how many minutes past the last 30-minute mark
    minutes_to_subtract = now.minute % 30
    rounded = now.replace(second=0, microsecond=0) - timedelta(minutes=minutes_to_subtract)
    return rounded.strftime('%Y-%m-%dT%H:%M:%S.0000000Z')
'''

# Example usage
if __name__ == "__main__":
    # refer to https://toolkit.solcast.com.au/ for details
    if len(sys.argv) > 2: # retrieve solcast data and save to DB for further use
        apiKey = sys.argv[1] # os.environ.get("apiKey", "")         # API Key
        resourceID = sys.argv[2] # os.environ.get("resourceID", "") # resource ID
        logDetail = sys.argv[3] # os.environ.get("IS_DEBUG", "False") == "True"

        solcastResponse = getSolarProductionEstimate(resourceID, apiKey)
        print(datetime.now(), " ", solcastResponse)

        if solcastResponse != "":            
            client = getClient()

            saveSolarProductionEstimateToDB(solcastResponse, client, logDetail)
        else:
            print(datetime.now(), "Error reading forecast")
    else: # calculate which targets are met
        client = getClient()

        sc = Solcast(client, 5120, 4600, 1500, 1024, os.environ.get("IS_DEBUG", "True") == "True")
        gridTied = os.environ.get("GRID_TIED", "").split(",") 
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

        
