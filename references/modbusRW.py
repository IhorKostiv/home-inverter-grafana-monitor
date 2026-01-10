import time
import minimalmodbus
import sys

device_port = sys.argv[1]
device_id = int(sys.argv[2])
baud_rate = int(sys.argv[3])
register = int(sys.argv[4])
if len(sys.argv) > 5:
    value = int(sys.argv[5])
else:
    value = -1

SERPORT = f'/dev/tty{device_port}'
SERTIMEOUT = 0.5
SERBAUD = baud_rate

time.sleep(1)

i = minimalmodbus.Instrument(SERPORT, device_id)
i.serial.timeout= SERTIMEOUT
i.serial.baudrate = SERBAUD
i.debug = True
i.clear_buffers_before_each_transaction = True

result = i.read_register(register)
print("{0} was {1}".format(register, result))

if value >=0 :
    time.sleep(0.1)

    i.write_register(register, value)
    print("{0} now {1}".format(register, value))