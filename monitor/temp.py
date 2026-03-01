
from venv import create
from influxdb import InfluxDBClient
#from influxdb_client.client.write_api import SYNCHRONOUS, ASYNCHRONOUS

import os
from datetime import datetime, timezone
#from zoneinfo import ZoneInfo
import pytz

def dtKyiv(t:datetime):
    return t.astimezone(pytz.timezone('Europe/Kyiv')).strftime('%Y-%m-%d %H:%M')

DB_HOST = os.environ.get("DB_HOST", "inverter")
DB_PORT = int(os.environ.get("DB_PORT", "8086"))
DB_USERNAME = os.environ.get("DB_USERNAME", "root")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "root")
DB_NAME = os.environ.get("DB_NAME", "ups")

client = InfluxDBClient(DB_HOST, DB_PORT, DB_USERNAME, DB_PASSWORD, DB_NAME)

x = {} #'20:00', '20:30', '21:00', '21:30', '22:00', '22:30', '23:00', "23:30", '00:00', '00:30', '01:00', '01:30', '02:00', '02:30', '03:00', '03:30'}
MaxPowerLimit = 5120
TargetPower = 4900
LowPower = 1500
MinPower = 1024
CalcTime = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
#Estimate = 'pvEstimate10'
#Estimate = '(pvEstimate + pvEstimate10 + pvEstimate10 + pvEstimate10)/4'
Estimate = '(pvEstimate + pvEstimate10 + pvEstimate10)/3'
#Estimate = '(pvEstimate + pvEstimate10)/2'
#Estimate = '(pvEstimate + pvEstimate10)/2'
#Estimate = 'pvEstimate'

TargetDetected = None
LowDetected = None
MinDetected = None

LoadHistory = client.query("SELECT mean(""iPLoad"") FROM ""inverter"" WHERE time >= now() - 3d GROUP BY time(30m) tz('Europe/Kiev')")
LoadAverages = {} 
for table in LoadHistory: # compute average load approximation for each 30min slot using last 3 days data
    for record in table:
        t = datetime.strptime(record['time'], '%Y-%m-%dT%H:%M:%SZ').strftime('%H:%M')
        if not t in x: # ignore night time slots
            if record['mean'] is None:
                print(f"!!!\a No load data for {t}, skip")
            else:
                if t in LoadAverages:
                    LoadAverages[t] = int((LoadAverages[t] + int(record['mean'])) /2)
                else:
                    LoadAverages[t] = int(record['mean'])
        else:
            LoadAverages[t] = 2

BatteryRemain = list(client.query("SELECT last(\"bRemain\") * 25.6 FROM \"bms\"").get_points())[0]['last']
#cbe = None  # Closest Break Even
#cre = list(BatteryRemain.get_points())[0]['last'] # Closest Remain Estimate
#nbe = None # Next BreakEven
#nre = 0  # Next Remain Estimate
#print(f"{CalcTime} Remain {cre:.0f}W {nre:.0f}W")
print(f"{CalcTime} Remain {BatteryRemain:.0f}W {BatteryRemain/51.2:.0f}% for {Estimate}")

GenerationEstimates = client.query(f"SELECT {Estimate} as Estimate FROM \"solcast\" WHERE time >= '{CalcTime}'")

for table in GenerationEstimates:
    for record in table:
        d = datetime.strptime(record['time'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
        t = d.strftime('%H:%M')
        if t in LoadAverages:
            le = LoadAverages[t]      # Load Estimate, W
            ge = record['Estimate']     # Generation Estimate, W
            BatteryRemain +=(ge - le) * 0.5 # half hour interval)
            if BatteryRemain > MaxPowerLimit:
                BatteryRemain = MaxPowerLimit
                #print(f"Battery shall be fully charged at {d} UTC")
            if LowDetected is None and BatteryRemain <= LowPower:
                LowDetected = d
                print(f"Low level detected at {dtKyiv(LowDetected)} for {Estimate}")
            if TargetDetected is None and BatteryRemain >= TargetPower:
                TargetDetected = d
                print(f"Target level detected at {dtKyiv(TargetDetected)} for {Estimate}")
            if BatteryRemain <= MinPower:
                MinDetected = d
                print(f"!!!\a Battery would be depleted below {MinPower}W at {dtKyiv(d)}")
                break
            print(f"{dtKyiv(d)} load {le:.0f}W gen {ge:.0f}W Remain {BatteryRemain:.0f}W {BatteryRemain/51.20:.0f}%")

            '''
            if cbe is None:
                cre += (ge - le) * 0.5
                if cre > MaxPowerLimit:
                    cre = MaxPowerLimit
                if ge >= le: # we are generating more than consuming, set break even point
                    cbe = t
                    print(f"cbe {cbe} cre {cre:.0f} {cre/51.20:.0f}%")
                    nre = cre
                if cre <= LowPower and LowDetected is None:
                    LowDetected = d
                if cre >= TargetPower and TargetDetected is None:
                    TargetDetected = d
                    #break
            else: # we have break even point, accumulate generation till break even point
                if nbe is None:
                    nre += (ge - le) * 0.5
                    if nre > MaxPowerLimit:
                        nre = MaxPowerLimit
                    if ge <= le: # we are consuming more than generating, set next break even point
                        nbe = t
                        print(f"nbe {nbe} nre {nre:.0f} {nre/51.20:.0f}%")
                        cre = nre
                    if nre <= LowPower and LowDetected is None:
                        LowDetected = d
                    if nre >= TargetPower and TargetDetected is None:
                        TargetDetected = d
                    #break
                else: # we have next break even point, just print estimates
                    cre += (ge - le) * 0.5
                    if cre > MaxPowerLimit:
                        cre = MaxPowerLimit
                    if cre <= LowPower and LowDetected is None:
                        LowDetected = d
                    if cre >= TargetPower and TargetDetected is None:
                        TargetDetected = d
            print(f"{d.astimezone(ZoneInfo('Europe/Kyiv')).strftime('%Y-%m-%d %H:%M')} load {le:.0f}W gen {ge:.0f}W Remain {cre:.0f}W {cre/51.20:.0f}% {nre:.0f}W {nre/51.20:.0f}%")
            '''
        else:
            print(f"!!!\a {dtKyiv(d)} load ?? gen {record['Estimate']:.0f}W Remain {BatteryRemain:.0f}W {BatteryRemain/51.20:.0f}%")
            #print(f"{d.astimezone(ZoneInfo('Europe/Kyiv')).strftime('%Y-%m-%d %H:%M')} load ? gen {record['pvEstimate']:.0f}W cre {cre:.0f} {nre:.0f}W")

#print(f"Low level detected at {LowDetected}, Target level detected at {TargetDetected} for {Estimate}")
if TargetDetected is not None and (LowDetected is None or TargetDetected < LowDetected):
    print(f"Target level shall be reached first at {dtKyiv(TargetDetected)} for {Estimate}, Low at {LowDetected}")
elif LowDetected is not None:
    print(f"Low level could be reached first at {dtKyiv(LowDetected)}, Target at {TargetDetected} for {Estimate}")
else:
    print(f"Neither target nor low levels would be reached for {Estimate}")

