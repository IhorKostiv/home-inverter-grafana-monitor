import datetime
from dateutil import parser
from influxdb import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS, ASYNCHRONOUS

import requests
import json
import os

def solarProductionEstimate(lat: float, lon: float, dec: int, az: int, kwp: float, damping: str = "0") -> str:
    url = f"https://api.forecast.solar/estimate/watts/{lat}/{lon}/{dec}/{az}/{kwp}?damping={damping}" # ?actual=<float kWh>
#    url = f"https://api.meteosource.com/v1/solar?date={date}&lat={lat}&lon={lon}&modulePower={module_power}&orientation={orientation}&tilt={tilt}&key={api_key}"
    
    response = requests.get(url)
    
    # Check if the request was successful
    if response.status_code == 200:
        return response.text
    else:
        return "" # "error: Failed to fetch data"

def pvEstimate(currentTime: datetime, solarData) -> int:

    p1 = 0
    t1 = currentTime
    p2 = 0
    t2 = currentTime
    
    for i, t in enumerate(solarData):
        p = solarData[t]
        tt = parser.parse(t)
        if currentTime > tt:
            p1 = p
            t1 = tt
        else:
            if currentTime < tt:
                p2 = p
                t2 = tt
                break
            else:
                if currentTime == tt:
                    return p

#        print(f"index {i} time {t} estimate {p}")

    d1 = currentTime - t1
 #   d2 = t2 - current_time
    d = t2 - t1

    avg = p1 + ((p2 - p1) * d1.total_seconds() / d.total_seconds()) # linear approximation
    
    #print(f"estimate {avg}@{currentTime} between {p1}@{t1} and {p2}"@{t2})
    return avg

# Example usage
if __name__ == "__main__":
                                                    # refer to https://doc.forecast.solar/api:estimate for details
    lat = os.environ.get("LATITUDE", "49.842")      # latitude of location, -90 (south) … 90 (north); handeled with a precission of 0.0001 or ~10 m
    lon = os.environ.get("LONGITUDE", "24.0316")    # longitude of location, -180 (west) … 180 (east); handeled with a precission of 0.0001 or ~10 m
    az = os.environ.get("AZIMUTH", "20")            # plane azimuth, -180 … 180 (-180 = north, -90 = east, 0 = south, 90 = west, 180 = north); integer
    dec = os.environ.get("DECLINTION", "70")        # plane declination, 0 (horizontal) … 90 (vertical) - always in relation to the earth's surface; integer
    kwp = os.environ.get("POWER", "1.8")            # installed modules power in kWatt; float
    damping = os.environ.get("DAMPING","0")         # https://doc.forecast.solar/damping
    isDebug = os.environ.get("IS_DEBUG", "False") == "True"

    #forecastSolarResponse = '{"result":{"2024-10-09 07:36:52":0,"2024-10-09 08:00:00":59,"2024-10-09 09:00:00":158,"2024-10-09 10:00:00":266,"2024-10-09 11:00:00":327,"2024-10-09 12:00:00":377,"2024-10-09 13:00:00":464,"2024-10-09 14:00:00":533,"2024-10-09 15:00:00":510,"2024-10-09 16:00:00":354,"2024-10-09 17:00:00":193,"2024-10-09 18:00:00":114,"2024-10-09 18:45:09":0,"2024-10-10 07:38:26":0,"2024-10-10 08:00:00":67,"2024-10-10 09:00:00":240,"2024-10-10 10:00:00":550,"2024-10-10 11:00:00":891,"2024-10-10 12:00:00":1145,"2024-10-10 13:00:00":1270,"2024-10-10 14:00:00":1168,"2024-10-10 15:00:00":847,"2024-10-10 16:00:00":557,"2024-10-10 17:00:00":311,"2024-10-10 18:00:00":159,"2024-10-10 18:43:03":0},"message":{"code":0,"type":"success","text":"","pid":"5zRxtV3F","info":{"latitude":49.842,"longitude":24.0316,"distance":0,"place":"Town Hall, Rynok Square, 1, Lviv Raion, Lviv, Lviv Oblast, 79008, Ukraine","timezone":"Europe/Kiev","time":"2024-10-09T22:32:59+03:00","time_utc":"2024-10-09T19:32:59+00:00"},"ratelimit":{"zone":"IP 194.44.50.199","period":3600,"limit":12,"remaining":10}}}'
    forecastSolarResponse = solarProductionEstimate(lat, lon, dec, az, kwp, damping)    
    print(datetime.datetime.now(), " ", forecastSolarResponse)

    if forecastSolarResponse != "":
        solarData = json.loads(forecastSolarResponse)
        Response = solarData["result"]
        json_body = [
            {
                "measurement": "forecast",
             #   "tags": { "lat": lat, "lon": lon, "az": az, "dec": dec, "kwp": kwp, "damping": damping },
                "fields": { "Response": str(Response) }
             }
        ]

        DB_HOST = os.environ.get("DB_HOST", "sandbox")
        DB_PORT = int(os.environ.get("DB_PORT", "8086"))
        DB_USERNAME = os.environ.get("DB_USERNAME", "root")
        DB_PASSWORD = os.environ.get("DB_PASSWORD", "root")
        DB_NAME = os.environ.get("DB_NAME", "ups")

        client = InfluxDBClient(DB_HOST, DB_PORT, DB_USERNAME, DB_PASSWORD, DB_NAME)

        if isDebug:
            print(datetime.datetime.now(), " ", json_body)

        client.write_points(json_body)
    else:
        print(datetime.datetime.now(), "Error reading forecast")