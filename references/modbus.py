import minimalmodbus
import sys

device_id = int(sys.argv[1])
baud_rate = int(sys.argv[2])
registers_from = int(sys.argv[3])
registers_to = int(sys.argv[4])
forArray = len(sys.argv)>5 and str(sys.argv[5]).upper() == "TRUE"

SERPORT = '/dev/ttyUSB0'
SERTIMEOUT = 0.5
SERBAUD = baud_rate

i = minimalmodbus.Instrument(SERPORT, device_id)
i.serial.timeout= SERTIMEOUT
i.serial.baudrate = SERBAUD
i.debug = True
i.clear_buffers_before_each_transaction = True

results = i.read_registers(registers_from, registers_to - registers_from)
for i, v in enumerate(results):
    if forArray:
        print(f"{v}, ", end="")
    else:
        print("{0} = {1}".format(i + registers_from, v))
if forArray:
    print(f"was for {registers_from} {registers_to}")
