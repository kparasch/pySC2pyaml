from pyaml.validation import DynamicValidation, register_schema
from pyaml.control.deviceaccess import DeviceAccess
from pyaml import PyAMLException

from .deviceaccess import pySCDeviceAccess
from .abstract_catalog import ACatalog
from .controlsystem import pySCControlSystem

@register_schema
class pySCCatalog(ACatalog, DynamicValidation):
    def __init__(self):
        super().__init__()
        self._refs: dict[tuple[int, str], DeviceAccess] = {}

    def resolve(self, key: str, control_system: pySCControlSystem | None = None) -> DeviceAccess:
        address, index = self._parse_key(key)
        cache_key = (id(control_system), key)

        if cache_key not in self._refs:
            self._refs[cache_key] = pySCDeviceAccess(address=address, index=index)

        return self._refs[cache_key]

    def _parse_key(self, key: str) -> tuple[str, int | None]:
        """
        Validate and split a catalog key into ``(attr_path, index)``.

        The ``index`` is ``None`` for plain attribute paths and an integer for
        indexed paths (``attr_path@index``).

        Raises
        ------
        pyaml.PyAMLException
            If the key is not a string, the attribute path does not have
            exactly four slash-separated components, or the index suffix is
            not a valid integer.
        """
        if not isinstance(key, str):
            raise PyAMLException(
                f"pySC catalog expects string keys, got {type(key).__name__}"
            )

        if "@" in key:
            attr_path, idx_str = key.rsplit("@", 1)
            try:
                index = int(idx_str)
            except ValueError as exc:
                raise PyAMLException(
                    f"pySC catalog invalid index '{idx_str}' in key '{key}'."
                ) from exc
        else:
            attr_path = key
            index = None

        parts = attr_path.split("/")
        if len(parts) != 3 or any(part == "" for part in parts):
            raise PyAMLException(
                f"pySC catalog cannot resolve invalid pySC address "
                f"reference '{key}'. Expected 'server/location/property' or "
                f"'server/location/property@index'."
            )

        return attr_path, index