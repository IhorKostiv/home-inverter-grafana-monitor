from ups import UPS, greenCell


inverter: UPS = greenCell.GreenCell("/dev/ttyUSB0")
sample = inverter.sample()

print("Measured: {0}".format(sample))
