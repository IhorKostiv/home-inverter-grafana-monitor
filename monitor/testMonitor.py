import sys
from ups._inverter_ import inverterMgr
from ups._constants_ import logDebug
from ups import greenCell, axioma #, must_ep3000, must_pv1800, must_ph18_5248

SUPPORTED_INVERTERS = {
    "GreenCell": greenCell.GreenCell,
    "Axioma": axioma.Axioma
#    "must-pv1800": must_pv1800.MustPV1800,
#    "must-ep3000": must_ep3000.MustEP3000,
#    "must-ph18-5248": must_ph18_5248.MustPH185248
}

if len(sys.argv) >= 3:
    if sys.argv[1] not in SUPPORTED_INVERTERS:
        print(f"Error: Unknown inverter model: {sys.argv[1]}")
        exit(1)
    inverter: inverterMgr = SUPPORTED_INVERTERS[sys.argv[1]](logDebug, sys.argv[2])
    json_body = inverter.jSON()
    inverter.Log(logDebug, json_body)
else:
    print("Usage: testMonitor.py <InverterModel> <InverterNode>")
    print("Example: python3 testMonitor.py GreenCell /dev/ttyUSB0")
    print("      or python3 testMonitor.py Axioma /dev/ttyACM0")