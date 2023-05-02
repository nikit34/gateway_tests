from dataclasses import dataclass
import logging
from opcua import ua


@dataclass(frozen=True)
class ItemBoolean:
    __slot__ = ["default", "type", "typecast"]
    default: bool = True
    type: ua.VariantType = ua.VariantType.Boolean
    typecast: object = bool


@dataclass(frozen=True)
class ItemInt:
    __slot__ = ["default", "type", "typecast"]
    default: int = 0
    type: ua.VariantType = ua.VariantType.Int32
    typecast: object = int


@dataclass(frozen=True)
class ItemLong:
    __slot__ = ["default", "type", "typecast"]
    default: int = 0
    type: ua.VariantType = ua.VariantType.Int64
    typecast: object = int


@dataclass(frozen=True)
class ItemDouble:
    __slot__ = ["default", "type", "typecast"]
    default: float = 0.0
    type: ua.VariantType = ua.VariantType.Double
    typecast: object = float


@dataclass(frozen=True)
class ItemString:
    __slot__ = ["default", "type", "typecast"]
    default: bool = True
    type: ua.VariantType = ua.VariantType.String
    typecast: object = str


@dataclass(frozen=True)
class MapTypes:
    __slot__ = ["Boolean", "Int", "Long", "Double", "String"]
    Boolean: ItemBoolean = ItemBoolean
    Int: ItemInt = ItemInt
    Long: ItemLong = ItemLong
    Double: ItemDouble = ItemDouble
    String: ItemString = ItemString

    def __contains__(self, item):
        return item in list(self.__annotations__.keys())

    def __getitem__(self, key):
        return super().__getattribute__(key)


@dataclass()
class NamesPolitics:
    __slot__ = [
        "none",
        "Basic256Sha256_SignAndEncrypt",
        "Basic256Sha256_Sign",
        "Basic256_SignAndEncrypt",
        "Basic256_Sign",
        "Basic128Rsa15_SignAndEncrypt",
        "Basic128Rsa15_Sign"
    ]
    none: ua.SecurityPolicyType = ua.SecurityPolicyType.NoSecurity
    Basic256Sha256_SignAndEncrypt: ua.SecurityPolicyType = ua.SecurityPolicyType.Basic256Sha256_SignAndEncrypt
    Basic256Sha256_Sign: ua.SecurityPolicyType = ua.SecurityPolicyType.Basic256Sha256_Sign
    Basic128Rsa15_SignAndEncrypt: ua.SecurityPolicyType = ua.SecurityPolicyType.Basic128Rsa15_SignAndEncrypt
    Basic128Rsa15_Sign: ua.SecurityPolicyType = ua.SecurityPolicyType.Basic128Rsa15_Sign
    Basic256_SignAndEncrypt: ua.SecurityPolicyType = ua.SecurityPolicyType.Basic256_SignAndEncrypt
    Basic256_Sign: ua.SecurityPolicyType = ua.SecurityPolicyType.Basic256_Sign

    @staticmethod
    def _up_first_character_(names):
        for name in names:
            name = name[0].upper() + name[1:]
            yield name

    def __iter__(self):
        for item in list(self.__annotations__.keys()):
            yield item

    def __iter_by_values__(self):
        for item in list(self.__annotations__.values()):
            yield item

    def iter(self):
        iter_after_crutch = self._up_first_character_(self.__iter__())
        for name, item in zip(iter_after_crutch, self.__iter_by_values__()):
            if name == "None":
                yield name, item["NoSecurity"]
            else:
                yield name, item[name]

    def __getitem__(self, key):
        return super().__getattribute__(key)


class LogMode:
    level_modes = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
        False: None
    }

    def __init__(self, mode):
        if mode not in [False, "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            raise TypeError("'LogMode' maybe only: False, 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'")
        self.log = self.level_modes[mode]
        self.mode = mode
        self.configured = []
