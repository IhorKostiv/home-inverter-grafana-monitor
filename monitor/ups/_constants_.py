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
txtGCAlways = "Always" # Grid Charging Always Enabled
txtGCNever = "Never" # Grid Charging Disabled