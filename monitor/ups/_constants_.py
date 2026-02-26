from datetime import datetime
from zoneinfo import ZoneInfo

# log levels: 0-Error, 1-Write, 2-Read, 3-Debug
logError = 0
logWrite = 1
logWarning = 1
logRead  = 2
logDebug = 3

# inverter energy use modes
txtNil = "Nil" # no energy use mode, should not be used
txtSOL = "SOL" # 
txtSBU = "SBU" # Solar and Battery used to power load, Unility used last
txtSUB = "SUB" # Solar is mixed to Utility to power load, Battery used as backup
txtUTI = "UTI" # Utility used to power load, Solar only used to charge battery

# Battery charger source
txtCSO = "CSO" # Solar charges battery first, if no solar then Grid charges battery
txtSNU = "SNU" # Solar power and Utility used to charge battery
txtOSO = "OSO" # Only Solar charges battery

# Solar use priorities
txtLBU = "LBU" # power Load first
txtBLU = "BLU" # charge Battery first

# Grid charging options
txtGCAlways = "Always" # Grid Charging Always Enabled - overall shall never be used, unless there is a dumb battery and underpower solar field
txtGCEmergency = "Emergency" # Grid Charging Enabled when battery is low or risk being depleted
txtGCNoSolar = "NoSolar" # charge when there is no solar production
txtGCNever = "Never" # Grid Charging Disabled
# there is also an option to specify time range, i.e. 23:00-07:00 to benefit from low overnight pricing when needed

def timeInRange(range: str, default: bool = False) -> bool:
    # Return True if current Kyiv time falls within a HH:MM-HH:MM range.
    # The range may span midnight (e.g. "23:00-07:00"). The comparison is inclusive of both endpoints. 
    # The function is forgiving of non-standard input and returns default if parsing fails.
    now = datetime.now(ZoneInfo("Europe/Kyiv"))
    try:
        parts = range.split("-")
        if len(parts) != 2:
            return False
        def _parse(t: str):
            h, m = map(int, t.split(":"))
            return datetime(1,1,1,h,m).time()
        t_from = _parse(parts[0])
        t_to = _parse(parts[1])
    except Exception:
        return default

    current = now.time()
    if t_from <= t_to:
        return t_from <= current <= t_to
    else:  # overnight range
        return current >= t_from or current <= t_to