import os
from ups import UPS, greenCell


inverter: UPS = greenCell.GreenCell("/dev/ttyUSB0", True)
sample = inverter.sample()

print("Measured: {0}".format(sample))

INVERTER_MODEL = os.environ.get("INVERTER_MODEL", "GreenCell")

json_body = sample.jSON(INVERTER_MODEL)

print(json_body)
