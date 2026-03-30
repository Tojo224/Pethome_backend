from enum import Enum


class RoleEnum(str, Enum):
    ADMIN = "ADMIN"
    VETERINARIAN = "VETERINARIAN"
    CLIENT = "CLIENT"