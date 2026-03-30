from enum import Enum


class RoleEnum(str, Enum):
    ADMIN = "ADMIN"
    VETERINARIAN = "VETERINARIAN"
    CLIENT = "CLIENT"

    @classmethod
    def values(cls):
        return [role.value for role in cls]