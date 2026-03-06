from datetime import datetime
from zoneinfo import ZoneInfo

class logger(object):
    def __init__(self, logDetail: int, **kwargs):
        self.LogDetail: int = logDetail

    def Log(self, logLevel: int, message: str): # log 0-Error, 1-Write, 2-Read, 3-Debug
        if self.LogDetail >= logLevel:
            print(f"{logLevel}> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\t{message}", flush=True)

class device(logger): # base class for everything
    def __init__(self, logDetail: int, **kwargs):
        super().__init__(logDetail = logDetail, **kwargs)
        self.measurement = "device"
        self.uKey = "default"

    @staticmethod
    def addText(t1:str, t2: str, separator: str = ", "): # used to concatenate strings in warning and error messages to add comma separation where needed
        return t1 + separator + t2 if t1 != "" else t2
    @staticmethod
    def dtKyiv(t:datetime):
        return t.astimezone(ZoneInfo('Europe/Kyiv')).strftime('%d-%H:%M')
    @staticmethod
    def signedInt(value): # used to extract battery power and current values
        return (value ^ 0x8000) - 0x8000 # convert unsigned to signed int
    @staticmethod
    def bitmaskText(newLine, Bitmask, Texts, separator: str = ", "): # used to convert error or warning bitmasks to text
        t = ""
        for b in Texts:
            if b & Bitmask == b:
                t = device.addText(t, Texts[b], separator)
        return ", " + t if newLine and t != "" else t

    def _addNotEmpty_(self, f: dict, key: str, e:any): # add only not empty values to json in order to save memory and bandwith
        if hasattr(self, key):
            v = getattr(self, key)
            if v != e:
                if isinstance(v, list):
                    for i, vi in enumerate(v, 1):
                        f[f"{key}{i}"] = vi
                else:
                    f[key] = v
    def _getMandatoryFields_(self) -> dict: # override in child classes to return mandatory fields
        return {}
    def _getOptionalValues_(self) -> list: # override in child classes to return optional fields as list of name and empty value pairs
        return []
    def jSON(self) -> str:
        f = self._getMandatoryFields_()
        for key, value in self._getOptionalValues_():
            self._addNotEmpty_(f, key, value)
        return [{"measurement": self.measurement, "tags": { "uKey": self.uKey },"fields": f }]

# Example usage
if __name__ == "__main__":
    raise NotImplementedError("This is a base class. Please implement the child class and override the necessary methods.")