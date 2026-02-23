if __name__ == "_bms_":
    from __init__ import device
else:
    from ups import device

class bms(device): # base class for battery management system
    def __init__(self, logDetail: int, **kwargs):
        super().__init__(logDetail = logDetail, **kwargs)
        self.measurement = "bms"

        self.bCurrent: float = 0.0
        self.bVoltage: float = 0.0
        self.bSOC: int = 0
        self.bSOH: int = 0
        self.bRemain: float = 0.0
        self.bFullCapacity: int = 0
        self.bDesignCapacity: int = 0
        self.bCycles: int = 0
        self.bWarning: str = ""
        self.bProtection: str = ""
        self.bFaults: str = ""
        self.bStatus: str = ""
        self.bBalance: str = ""
        self.bVoltages = {}
        self.bTemperatures = {}
        self.bMOSFETtemperature: float = 0.0
        self.bEnvironmentTemperature: float = 0.0

    @property
    def CurrentPower(self):
        return self.bVoltage * self.bRemain
    
    def _getMandatoryFields_(self) -> dict:
        return {
            "bCurrent": self.bCurrent,
            "bVoltage": self.bVoltage, 
            "bSOC": self.bSOC,
            "bRemain": self.bRemain,
            "bCycles": self.bCycles,
        }
    def _getOptionalValues_(self) -> list:
        return [
            ("bSOH", 0),
            ("bFullCapacity", 0),
            ("bDesignCapacity", 0),
            ("bWarning", ''),
            ("bProtection", ''),
            ("bFaults", ''),
            ("bStatus", ''),
            ("bBalance", ''),
            ("bVoltages", []),
            ("bTemperatures", []),
            ("bMOSFETtemperature", 0),
            ("bEnvironmentTemperature", 0)
        ]
