from ups import UPS, greenCell


inverter: UPS = greenCell.GreenCell("/dev/ttyUSB0")
sample = inverter.sample()

print("Measured: {0}".format(sample))

INVERTER_MODEL = os.environ.get("INVERTER_MODEL", "GreenCell")
json_body = [
    {
        "measurement": "inverter",
        "tags": {
            "model": INVERTER_MODEL,
            "pvWorkState": sample.pvWorkState,
            "pvMpptState": sample.pvMpptState,
            "pvChargingState": sample.pvChargingState,
            "pvBatteryRelay": sample.pvBatteryRelay,
            "pvRelay": sample.pvRelay,
            "pvError": sample.pvError,
            "pvWarning": sample.pvWarning,
            "iWorkState": sample.iWorkState,
            "iRelayState": sample.iRelayState,
            "iGridRelayState": sample.iGridRelayState,
            "iLoadRelayState": sample.iLoadRelayState,
            "iError": sample.iError,
            "iWarning": sample.iWarning
        },
        "fields": {
            "pvVoltage": sample.pvVoltage,
            "pvBatteryVoltage": sample.pvBatteryVoltage,
            "pvChargerCurrent": sample.pvChargerCurrent,
            "pvChargerPower": sample.pvChargerPower,
            "pvRadiatorTemperature": sample.pvRadiatorTemperature,
            "pvAccumulatedPower": sample.pvAccumulatedPower,
            "iBatteryVoltage": sample.iBatteryVoltage,
            "iVoltage": sample.iVoltage,
            "iGridVoltage": sample.iGridVoltage,
            "iPInverter": sample.iPInverter,
            "iPGrid": sample.iPGrid,
            "iPLoad": sample.iPLoad,
            "iLoadPercent": sample.iLoadPercent,
            "iSInverter": sample.iSInverter,
            "iSGrid": sample.iSGrid,
            "iSLoad": sample.iSLoad,
            "iRadiatorTemperature": sample.iRadiatorTemperature,
            "iAccumulatedLoadPower": sample.iAccumulatedLoadPower,
            "iAccumulatedDischargerPower": sample.iAccumulatedDischargerPower,
            "iAccumulatedSelfusePower": sample.iAccumulatedSelfusePower,
            "iBattPower": sample.iBattPower,
            "iBattCurrent": sample.iBattCurrent
        }
    }
]

print(json_body)
