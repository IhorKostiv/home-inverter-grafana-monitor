from datetime import datetime
from influxdb import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS, ASYNCHRONOUS

import requests
import json
import os

def get_solar_production_estimate(lat: float, lon: float, dec: int, az: int, kwp: float, damping: str = "0") -> str:
    url = f"https://api.forecast.solar/estimate/watts/{lat}/{lon}/{dec}/{az}/{kwp}?damping={damping}" # ?actual=<float kWh>
#    url = f"https://api.meteosource.com/v1/solar?date={date}&lat={lat}&lon={lon}&modulePower={module_power}&orientation={orientation}&tilt={tilt}&key={api_key}"
    
    response = requests.get(url)
    
    # Check if the request was successful
    if response.status_code == 200:
        return response.text
    else:
        return "" # "error: Failed to fetch data"

def pvEstimate(current_time: datetime, solar_data) -> int:

    p1 = 0
    t1 = current_time
    p2 = 0
    t2 = current_time
    
    for i, t in enumerate(solar_data['result']):
        p = solar_data['result'][t]
        tt = parser.parse(t)
        if current_time > tt:
            p1 = p
            t1 = tt
        else:
            if current_time <= tt:
                p2 = p
                t2 = tt
                break

#        print(f"index {i} time {t} estimate {p}")

    d1 = current_time - t1
 #   d2 = t2 - current_time
    d = t2 - t1

    avg = p1 + ((p2 - p1) * d1.total_seconds() / d.total_seconds()) # linear approximation

 #   print(f"estimate {avg} between {p1} and {p2}")
    return avg

# Example usage
if __name__ == "__main__":
                                                    # refer to https://doc.forecast.solar/api:estimate for details
    lat = os.environ.get("LATITUDE", "49.842")      # latitude of location, -90 (south) … 90 (north); handeled with a precission of 0.0001 or abt. 10 m
    lon = os.environ.get("LONGITUDE", "24.0316")   # longitude of location, -180 (west) … 180 (east); handeled with a precission of 0.0001 or abt. 10 m
    az = os.environ.get("AZIMUTH", "20")            # plane azimuth, -180 … 180 (-180 = north, -90 = east, 0 = south, 90 = west, 180 = north); integer
    dec = os.environ.get("DECLINTION", "70")        # plane declination, 0 (horizontal) … 90 (vertical) - always in relation to the earth's surface; integer
    kwp = os.environ.get("POWER", "1.8")            # installed modules power in kilo watt; float
    damping = os.environ.get("DAMPING","0")   # https://doc.forecast.solar/damping

    #forecastSolarResponse = '{"result":{"2024-10-09 07:36:52":0,"2024-10-09 08:00:00":59,"2024-10-09 09:00:00":158,"2024-10-09 10:00:00":266,"2024-10-09 11:00:00":327,"2024-10-09 12:00:00":377,"2024-10-09 13:00:00":464,"2024-10-09 14:00:00":533,"2024-10-09 15:00:00":510,"2024-10-09 16:00:00":354,"2024-10-09 17:00:00":193,"2024-10-09 18:00:00":114,"2024-10-09 18:45:09":0,"2024-10-10 07:38:26":0,"2024-10-10 08:00:00":67,"2024-10-10 09:00:00":240,"2024-10-10 10:00:00":550,"2024-10-10 11:00:00":891,"2024-10-10 12:00:00":1145,"2024-10-10 13:00:00":1270,"2024-10-10 14:00:00":1168,"2024-10-10 15:00:00":847,"2024-10-10 16:00:00":557,"2024-10-10 17:00:00":311,"2024-10-10 18:00:00":159,"2024-10-10 18:43:03":0},"message":{"code":0,"type":"success","text":"","pid":"5zRxtV3F","info":{"latitude":49.842,"longitude":24.0316,"distance":0,"place":"Town Hall, Rynok Square, 1, Lviv Raion, Lviv, Lviv Oblast, 79008, Ukraine","timezone":"Europe/Kiev","time":"2024-10-09T22:32:59+03:00","time_utc":"2024-10-09T19:32:59+00:00"},"ratelimit":{"zone":"IP 194.44.50.199","period":3600,"limit":12,"remaining":10}}}'
    forecastSolarResponse = get_solar_production_estimate(lat, lon, dec, az, kwp, damping)    
    
    if forecastSolarResponse != "":
        solar_data = json.loads(forecastSolarResponse)
        Response = solar_data["result"]
        json_body = [
            {
                "measurement": "forecast",
                "tags": { "lat": lat, "lon": lon, "az": az, "dec": dec, "kwp": kwp, "damping": damping },
                "fields": { "Response": Response }
             }
        ]

        DB_HOST = os.environ.get("DB_HOST", "192.168.77.34")
        DB_PORT = int(os.environ.get("DB_PORT", "8086"))
        DB_USERNAME = os.environ.get("DB_USERNAME", "root")
        DB_PASSWORD = os.environ.get("DB_PASSWORD", "root")
        DB_NAME = os.environ.get("DB_NAME", "ups")

        client = InfluxDBClient(DB_HOST, DB_PORT, DB_USERNAME, DB_PASSWORD, DB_NAME)

        print(datetime.now(), " ", json_body)

        client.write_points(json_body)
    else:
        print(datetime.datetime.now(), "Error reading forecast")