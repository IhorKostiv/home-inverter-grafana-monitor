import os
import datetime
from ups import UPS, greenCell


inverter: UPS = greenCell.GreenCell("/dev/ttyUSB0")
sample = inverter.sample(True)

print("Measured: {0}".format(sample))

INVERTER_MODEL = os.environ.get("INVERTER_MODEL", "GreenCell")

json_body = sample.jSON(INVERTER_MODEL)

print(datetime.datetime.now(), " ", json_body)

