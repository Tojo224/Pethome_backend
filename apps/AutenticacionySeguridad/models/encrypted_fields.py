import json
from typing import Any, Iterable, List, Optional

from django.conf import settings
from django.db import models
from cryptography.fernet import Fernet, InvalidToken, MultiFernet


def _get_key_list() -> List[str]:
    raw_keys: Optional[Any] = getattr(settings, "BITACORA_SECRET_KEYS", None)
    if raw_keys is None:
        raw_keys = getattr(settings, "BITACORA_SECRET_KEY", None)

    if isinstance(raw_keys, (list, tuple)):
        keys = [str(item).strip() for item in raw_keys]
    else:
        keys = [item.strip() for item in str(raw_keys or "").split(",")]

    keys = [key for key in keys if key]
    if not keys:
        raise RuntimeError("BITACORA_SECRET_KEY(S) no configurada")

    return keys


def _build_fernet() -> MultiFernet:
    keys = _get_key_list()
    return MultiFernet([Fernet(key.encode("ascii")) for key in keys])


class EncryptedJSONField(models.BinaryField):
    """
    Stores a dict as encrypted JSON in a BYTEA column.
    """

    def to_python(self, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, dict):
            return value
        return self._decrypt_value(value)

    def from_db_value(self, value: Any, expression: Any, connection: Any) -> Any:
        if value is None:
            return None
        return self._decrypt_value(value)

    def get_prep_value(self, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, (bytes, bytearray, memoryview)):
            return bytes(value)

        json_bytes = json.dumps(value, default=str, ensure_ascii=True).encode("utf-8")
        return _build_fernet().encrypt(json_bytes)

    def _decrypt_value(self, value: Any) -> Any:
        try:
            raw = bytes(value)
            decrypted = _build_fernet().decrypt(raw)
            return json.loads(decrypted.decode("utf-8"))
        except InvalidToken:
            return {"error": "No se pudo descifrar el payload"}
