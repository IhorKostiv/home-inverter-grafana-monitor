import time
import minimalmodbus
import sys
from datetime import datetime

commands = {
    "13.3V": [10103, 133], "13.6V": [10103, 136], "13.9V": [10103, 139], "14.0V": [10103, 140],
    #"26.6V": [10103, 266], "27.8V": [10103, 278], "27.9V": [10103, 279], 
    "SBU"  : [20109, 1], "UTI"  : [20109, 3], #"SUB"  : [20109, 2],
    "LBU"  : [20112, 0], "BLU"  : [20112, 1],
    "CSO"  : [20143, 0], "SNU"  : [20143, 2], "OSO"  : [20143, 3],
    }
if len(sys.argv) < 5:
    print("Usage: modbusRW.py Port ID Baud Command|Register (Value)")
    print("Sample:\nGreenCell inverter: modbusRW.py USB0 4 19200 ", end="")
    for cmd in commands:
        print(cmd, end="|")
    print("register (value)\nMust BMS balance deviation, 15mV: modbusRW.py ACM0 1 9600 106 15")
    exit(1)

device_port = sys.argv[1]
device_id = int(sys.argv[2])
baud_rate = int(sys.argv[3])
cmd = sys.argv[4].upper()
if cmd in commands:
    register = commands[cmd][0]
    value = commands[cmd][1]
else:
    register = int(cmd)
    value = int(sys.argv[5]) if len(sys.argv) > 5 else -1

SERPORT = f'/dev/tty{device_port}'
SERTIMEOUT = 0.5
SERBAUD = baud_rate

s = 20 - datetime.now().second
if s > 0:
    print(f"Wait {s}s...")
    time.sleep(s+1)

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